# coding: utf-8
#         app: metas
#      module: views
#        date: miércoles, 23 de mayo de 2018 - 11:05
# description: Vistas para las metas
# pylint: disable=W0613,R0201,R0903

from django.views.generic import TemplateView
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from .models import Rol, Site, Member
from .forms import AddRolForm, AddSiteForm, AddMemberForm


class MetasIndex(TemplateView):
    template_name = 'metas/index.html'


class MetasAddMember(CreateView):
    model = Member
    form_class = AddMemberForm
    success_url = reverse_lazy('metas:add_member')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        members = Member.objects.all().order_by('role__order')
        context.update({'members': members})
        return context


class MetasAddSite(CreateView):
    model = Site
    form_class = AddSiteForm
    success_url = reverse_lazy('metas:add_site')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sites = Site.objects.all()
        context.update({'sites': sites})
        return context


class MetasAddRol(CreateView):
    model = Rol
    form_class = AddRolForm
    success_url = reverse_lazy('metas:add_rol')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        roles = Rol.objects.all().order_by('order')
        context.update({'kpi_path': True, 'roles': roles})
        return context
