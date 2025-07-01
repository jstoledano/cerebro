# -*- coding: UTF-8 -*-

#         app: org.toledano.yo
#      módulo: blog.templatetags.extra
# descripción: Funciones auxiliares para la plantilla
#       autor: Javier Sanchez Toledano
#       fecha: lunes, 21 de marzo de 2016

import os
import re
from django import template


register = template.Library()


@register.simple_tag
def current(request, pattern):
    try:
        if re.search(pattern, request.path):
            return 'active'
    except:
        return ''


@register.filter
def disqus_hash(value):
    return value.replace("/", "_")


@register.filter
def basename(value):
    """Extrae el nombre del archivo de una ruta"""
    return os.path.basename(value)