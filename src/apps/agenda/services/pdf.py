"""XeLaTeX rendering for the weekly and daily INE agenda."""
import os
import shlex
import shutil
import subprocess
from datetime import date
from pathlib import Path

from django.conf import settings


MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
WEEKDAYS = (
    "lunes", "martes", "mi\u00e9rcoles", "jueves", "viernes", "s\u00e1bado", "domingo",
)


def tex_escape(value) -> str:
    value = str(value or "")
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def _date_stamp(item, name: str) -> str:
    stamp = item.get(name) or {}
    raw = stamp.get("start", "") if isinstance(stamp, dict) else ""
    if not raw:
        return ""
    try:
        return date.fromisoformat(str(raw)[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return str(raw)[:10]


def _item_title(item) -> str:
    title = str(item.get("title") or "Sin t\u00edtulo").strip()
    task_id = str(item.get("id") or "").strip()
    if task_id:
        if title.upper() == task_id.upper():
            return "\\textbf{" + tex_escape(task_id) + "}"
        if title.upper().startswith((task_id + " ").upper()):
            title = title[len(task_id):].strip()
        return "\\textbf{" + tex_escape(task_id) + "} " + tex_escape(title)
    return tex_escape(title)


def render_task(item: dict, alternate: bool = False) -> str:
    """One readable agenda row; excludes state, plan, owner and monitor codes."""
    row_color = "\\rowcolor{rowAlt}\n" if alternate else ""
    scheduled = tex_escape(_date_stamp(item, "scheduled"))
    deadline = tex_escape(_date_stamp(item, "deadline"))
    return (
        row_color
        + "\\strut " + _item_title(item) + " & "
        + scheduled + " & " + deadline + r" \\" + "\n\\addlinespace[1.5mm]\n"
    )


def _day_label(key: str) -> str:
    try:
        current = date.fromisoformat(key)
    except (TypeError, ValueError):
        return tex_escape(key)
    return f"{WEEKDAYS[current.weekday()].capitalize()} {current.day} de {MONTHS[current.month-1]} de {current.year}"


def _period_label(start: date, end: date) -> str:
    if start == end:
        return f"{start.day} de {MONTHS[start.month - 1]} de {start.year}"
    if start.month == end.month and start.year == end.year:
        return f"Del {start.day} al {end.day} de {MONTHS[end.month - 1]} de {end.year}"
    if start.year == end.year:
        return (f"Del {start.day} de {MONTHS[start.month - 1]} "
                f"al {end.day} de {MONTHS[end.month - 1]} de {end.year}")
    return (f"Del {start.day} de {MONTHS[start.month-1]} de {start.year} "
            f"al {end.day} de {MONTHS[end.month-1]} de {end.year}")


def _xelatex_command(output_dir: Path, tex_path: Path) -> list[str]:
    """Build command args for native XeLaTeX or WSL XeLaTeX on Windows."""
    configured = getattr(settings, "AGENDA_XELATEX_COMMAND", "xelatex")
    executable = shlex.split(configured) if isinstance(configured, str) else list(configured)
    if not executable:
        raise RuntimeError("AGENDA_XELATEX_COMMAND esta vacia.")
    target_dir = str(output_dir.resolve())
    target_tex = str(tex_path.resolve())
    if os.name == "nt" and Path(executable[0]).name.lower() in {"wsl", "wsl.exe"}:
        prefix = executable[:-1]
        wslpath_cmd = prefix if "--exec" in prefix or "-e" in prefix else prefix + ["--exec"]

        def as_wsl_path(path: str) -> str:
            result = subprocess.run(
                wslpath_cmd + ["wslpath", "-a", path.replace("\\", "/")],
                capture_output=True, text=True, check=False,
            )
            converted = result.stdout.strip()
            if result.returncode != 0 or not converted:
                raise RuntimeError(
                    "No se pudo convertir la ruta de Windows para WSL: "
                    + path + ". " + (result.stderr or "").strip()
                )
            return converted

        target_dir = as_wsl_path(target_dir)
        target_tex = as_wsl_path(target_tex)
    return executable + [
        "-interaction=nonstopmode", "-halt-on-error",
        f"-output-directory={target_dir}", target_tex,
    ]


def _table_content(header_cells: list[str], column_spec: str, rows: str) -> str:
    """Longtable with gray headers repeated on page breaks."""
    header = " & ".join(
        "\\color{white}\\bfseries " + tex_escape(cell)
        for cell in header_cells
    ) + " " + "\\\\" + "\n"
    return (
        "\\begin{longtable}{" + column_spec + "}\n"
        + "\\rowcolor{ineGray}" + header
        + "\\endfirsthead\n"
        + "\\rowcolor{ineGray}" + header
        + "\\endhead\n"
        + rows
        + "\\end{longtable}\n"
    )


def _render_overdue(items: list[dict], cutoff: date) -> str:
    heading = "\\agendasection{01}{ACTIVIDADES VENCIDAS}\n"
    if not items:
        return heading + "\\noindent Sin actividades vencidas.\\par\n"
    rows = []
    for i, item in enumerate(items):
        alt = "\\rowcolor{rowAlt}\n" if i % 2 else ""
        rows.append(alt + tex_escape(_date_stamp(item, "deadline")) + " & "
                    + _item_title(item) + " " + "\\\\" + "\n\\addlinespace[1.5mm]\n")
    spec = r"@{}>{\centering\arraybackslash}p{2.8cm}>{\raggedright\arraybackslash}p{\dimexpr\linewidth-3.3cm\relax}@{}"
    return heading + _table_content(["Vencimiento", "Actividad"], spec, "".join(rows))


def _render_radar(items: list[dict], week_end: date) -> str:
    heading = "\\agendasection{03}{EN EL RADAR}\n"
    if not items:
        return heading + "\\noindent Sin próximos compromisos con fecha.\\par\n"
    rows = []
    for i, item in enumerate(items):
        alt = "\\rowcolor{rowAlt}\n" if i % 2 else ""
        day = date.fromisoformat(item["agenda_date"])
        milestone = tex_escape(item.get("date_kind") or "")
        label = "\\shortstack[c]{" + tex_escape(f"{day:%d/%m/%Y}") + "\\\\" + milestone + "}"
        rows.append(alt + label + " & " + _item_title(item)
                    + " " + "\\\\" + "\n\\addlinespace[1.5mm]\n")
    spec = r"@{}>{\centering\arraybackslash}p{2.8cm}>{\raggedright\arraybackslash}p{\dimexpr\linewidth-3.3cm\relax}@{}"
    return heading + _table_content(["Próximo hito", "Actividad"], spec, "".join(rows))


def generate_pdf(
    items: list[dict], start: date, end: date, output_dir: Path,
    *, overdue: list[dict] | None = None, radar: list[dict] | None = None,
    cutoff: date | None = None,
) -> Path:
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    title = "Agenda Diaria" if start == end else "Agenda Semanal"
    period = _period_label(start, end)
    grouped = {}
    for item in items:
        stamp = item.get("agenda_date")
        if not stamp:
            stamp = ((item.get("scheduled") or {}).get("start")
                     or (item.get("deadline") or {}).get("start") or "")[:10]
        grouped.setdefault(stamp or "Sin fecha", []).append(item)

    sections = []
    for key, day_items in sorted(grouped.items()):
        title_day = tex_escape(_day_label(key))
        rows = "".join(render_task(item, alternate=(i % 2 == 1)) for i, item in enumerate(day_items))
        sections.append(
            "\\agendaday{" + title_day + "}\n"
            "\\begin{longtable}{@{}>{\\raggedright\\arraybackslash}p{\\dimexpr\\linewidth-6.2cm\\relax}"
            ">{\\centering\\arraybackslash}p{2.7cm}>{\\centering\\arraybackslash}p{2.7cm}@{}}\n"
            "\\rowcolor{ineGray}\\color{white}\\bfseries Actividad & "
            "\\color{white}\\bfseries Inicio & "
            "\\color{white}\\bfseries Vencimiento \\\\\n"
            "\\endfirsthead\n"
            "\\rowcolor{ineGray}\\color{white}\\bfseries Actividad & "
            "\\color{white}\\bfseries Inicio & "
            "\\color{white}\\bfseries Vencimiento \\\\\n"
            "\\endhead\n"
            + rows + "\\end{longtable}\n"
        )

    weekly_section = "\\agendasection{02}{AGENDA SEMANAL}\n" if start != end else ""
    weekly_content = "\n".join(sections) if sections else "\\noindent Sin actividades para este periodo.\\par\n"
    content = weekly_section + weekly_content
    if start != end:
        if overdue is not None:
            if cutoff is None:
                raise ValueError("Se requiere fecha de corte para las vencidas.")
            content = _render_overdue(overdue, cutoff) + "\n" + content
        if radar is not None:
            content += "\n" + _render_radar(radar, end)

    template_path = Path(__file__).resolve().parents[1] / "tex" / "agenda.tex"
    template = template_path.read_text(encoding="utf-8")
    tex = (template.replace("@@TITLE@@", tex_escape(title))
            .replace("@@PERIOD@@", tex_escape(period))
            .replace("@@CONTENT@@", content))

    # XeLaTeX resolves relative images from the current working directory.
    logo = template_path.parent / "ine_logo_agenda.png"
    if not logo.is_file():
        raise RuntimeError(f"Falta el logotipo de la agenda: {logo}")
    shutil.copyfile(logo, output_dir / "ine_logo_agenda.png")

    basename = f"agenda-{start:%Y%m%d}-{end:%Y%m%d}"
    tex_path = output_dir / f"{basename}.tex"
    tex_path.write_text(tex, encoding="utf-8")
    result = subprocess.run(
        _xelatex_command(output_dir, tex_path),
        cwd=output_dir,
        capture_output=True, text=True, check=False,
    )
    pdf_path = output_dir / f"{basename}.pdf"
    if result.returncode != 0 or not pdf_path.is_file():
        log = output_dir / f"{basename}.log"
        detail = (log.read_text(encoding="utf-8", errors="replace")[-5000:]
                  if log.exists() else result.stderr[-3000:])
        raise RuntimeError(f"XeLaTeX fallo al generar el PDF. {detail}")
    return pdf_path
