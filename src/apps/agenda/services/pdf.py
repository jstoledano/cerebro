"""XeLaTeX PDF generation for daily and weekly agendas."""
import subprocess
import textwrap
from datetime import date
from pathlib import Path

from django.conf import settings


def tex_escape(value) -> str:
    text = str(value or "")
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def render_task(item: dict) -> str:
    props = item.get("properties") or {}
    state = item.get("state") or "EVENT"
    scheduled = (item.get("scheduled") or {}).get("start", "")
    deadline = (item.get("deadline") or {}).get("start", "")
    owner = props.get("OWNER", "")
    monitor = props.get("MONITOR", "")
    plan = props.get("PLAN", "")
    meta = "  |  ".join(part for part in [state, plan, owner, monitor,
                                         f"Programada: {scheduled}" if scheduled else "",
                                         f"Vence: {deadline}" if deadline else ""] if part)
    body_text = textwrap.shorten(" ".join((item.get("body", "") or "").split()), width=360, placeholder=" ...")
    body = tex_escape(body_text)
    return ("\\begin{tcolorbox}[colback=beigeLight,colframe=oxford,boxrule=.35pt,"
            "arc=2mm,left=2mm,right=2mm,top=1.5mm,bottom=1.5mm]\n"
            f"{{\\bfseries {tex_escape(item.get('title', 'Sin titulo'))}}}\\\\\n"
            f"{{\\small\\color{{muted}} {tex_escape(meta)}}}\\\\\n"
            f"{body}\n\\end{tcolorbox}\n")


def generate_pdf(items: list[dict], start: date, end: date, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    title = "Agenda diaria" if start == end else "Agenda semanal"
    period = start.strftime("%d/%m/%Y") if start == end else f"{start:%d/%m/%Y} - {end:%d/%m/%Y}"
    grouped = {}
    for item in items:
        key = item.get("agenda_date") or (item.get("scheduled") or item.get("deadline") or {}).get("start", "")[:10]
        grouped.setdefault(key or "Sin fecha", []).append(item)
    sections = []
    for key, day_items in sorted(grouped.items()):
        if key != "Sin fecha":
            try:
                day_value = date.fromisoformat(key)
                weekdays = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
                day_label = f"{weekdays[day_value.weekday()]} {day_value:%d/%m/%Y}"
            except ValueError:
                day_label = key
        else:
            day_label = key
        sections.append("\\section*{" + tex_escape(day_label) + "}\n\\begin{multicols}{2}\n" + "\n".join(render_task(item) for item in day_items) + "\n\\end{multicols}\n")
    cards = "\n".join(sections)
    if not cards:
        cards = r"\begin{tcolorbox}No hay actividades programadas para este periodo.\end{tcolorbox}"
    template_path = Path(__file__).resolve().parents[1] / "tex" / "agenda.tex"
    template = template_path.read_text(encoding="utf-8")
    tex = template.replace("@@TITLE@@", tex_escape(title))
    tex = tex.replace("@@PERIOD@@", tex_escape(period)).replace("@@CARDS@@", cards)
    basename = f"agenda-{start:%Y%m%d}-{end:%Y%m%d}"
    tex_path = output_dir / f"{basename}.tex"
    tex_path.write_text(tex, encoding="utf-8")
    command = getattr(settings, "AGENDA_XELATEX_COMMAND", "xelatex")
    result = subprocess.run(
        [command, "-interaction=nonstopmode", "-halt-on-error",
         f"-output-directory={output_dir}", str(tex_path)],
        capture_output=True, text=True, check=False,
    )
    pdf_path = output_dir / f"{basename}.pdf"
    if result.returncode != 0 or not pdf_path.is_file():
        log = output_dir / f"{basename}.log"
        detail = log.read_text(encoding="utf-8", errors="replace")[-5000:] if log.exists() else result.stderr[-3000:]
        raise RuntimeError(f"XeLaTeX fallo al generar el PDF. {detail}")
    return pdf_path
