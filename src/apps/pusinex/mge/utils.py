TOLERANCIA_AREA_M2 = 0.01


def geometria_cambio_informativo(
    geom_anterior,
    geom_nueva,
):
    if geom_anterior is None:
        return True

    if geom_anterior.equals(
        geom_nueva
    ):
        return False

    area_diferencia = (
        geom_anterior
        .sym_difference(
            geom_nueva
        )
        .area
    )

    return (
        area_diferencia
        > TOLERANCIA_AREA_M2
    )
