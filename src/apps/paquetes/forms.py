#-*- coding: utf-8 -*-
#       app: cmi.distribucion
#      desc: Generación de formularios para Distribucion de FCPVF

# Modelos
from django import forms
from .models import Envio, EnvioModulo
import datetime as dt

# Accesorios


# Formularios
class EnvioModuloForm(forms.ModelForm):
    class Meta:
        model = EnvioModulo
        fields = '__all__'

    mac = forms.CharField (
        widget=forms.TextInput(
            attrs={'class': 'col-md-1 form-control',}
        )
    )
    paquetes = forms.CharField (
        label='Número de paquetes',
        initial = 1,
        widget=forms.TextInput(
            attrs={'class': 'form-control',}
        )
    )
    formatos = forms.CharField (
        label='Número de FCPVF',
        widget=forms.TextInput(
            attrs={'class': 'form-control',}
        )
    )
    recibido_mac = forms.DateTimeField(
        widget=forms.TextInput(
            attrs={'class': 'form-control',}
        )
    )
    disponible_mac= forms.DateTimeField(
        widget=forms.TextInput(
            attrs={'class': 'form-control',}
        )
    )

    def clean_disponible_mac(self):
        data = self.cleaned_data
        menor = data['recibido_mac']
        mayor = data['disponible_mac']
        envio = data['lote']
        corte = envio.recibido_vrd
        if menor > mayor:
            raise forms.ValidationError('La fecha de recepción debe ser anterior a la disponibilidad')
        if menor < corte:
            raise forms.ValidationError('La fecha de recepción en MAC es anterior a la de recepción en VRD %s' % (corte))
        if mayor < corte:
            raise forms.ValidationError('La fecha de disponibilidad en MAC es anterior a la de recepción en  %s' % (corte))
        return data['disponible_mac']


class PreparacionForm(forms.ModelForm):
    class Meta:
        model = Envio
        fields = '__all__'

    DISTRITO =(
        ('#', '-- Seleccionar --'),
        ('1', '1: Apizaco - Distrito 01'),
        ('2', '2: Tlaxcala - Distrito 02'),
        ('3', '3: Zacatelco - Distrito 03')
        )
    distrito = forms.CharField (
        widget=forms.Select(
            choices=DISTRITO,
            attrs={'class':'form-control col-sm-4', 'onchange':"dynamic_Select('/distribucion/distrito/', this.value)"}
            )
        )
    lote = forms.CharField (
        widget=forms.TextInput(
            attrs={'class': 'input-small form-control',}
        ),
        initial = '18_29_',
    )
    num_prod = forms.CharField (
        label='Número de producción',
        widget=forms.TextInput(
            attrs={'class': 'input-small form-control',}
        ),
    )
    tipo_lote = forms.ChoiceField(
        widget=forms.RadioSelect(attrs={
            'class':'radio-inline'
        }),
        label="Tipo de Lote", choices=(
            ('ORD', 'ORD'),
            ('BIS', 'BIS'),
            ('REI', 'REI'),
            ('RA', 'RA'),
            ('EXT', 'EXT'),
            ),
        initial='ORD',
        help_text=u'Si aparece algún nuevo <strong>tipo de lote</strong>, comunícate con el <em>Equipo Técnico SGC</em>',
        )
    tipo_cinta = forms.ChoiceField(
        widget=forms.RadioSelect(attrs={
            'class':'radio-inline'
        }),
        label='Tipo de Cinta',
        choices=(
            ('1', 'Actualizacion'),
            ('2', 'Recurso de Apelación'),
            ),
        initial = '1',
        help_text=u'Si aparece algún nuevo <strong>tipo de cinta</strong>, comunícate con el <em>Equipo Técnico SGC</em>',
        )
    mac = forms.MultipleChoiceField(
        choices = EnvioModulo.MODULO,
        widget = forms.CheckboxSelectMultiple (
            attrs = {'inline': True,},
            )
        )
    credenciales =  forms.CharField (
        widget=forms.TextInput(
            attrs={'class': 'input-small form-control',}
        )
    )
    cajas = forms.CharField (
        widget=forms.TextInput(
            attrs={'class': 'input-small form-control',}
        )
    )
    envio_cnd = forms.DateTimeField(
        label='Fecha y Hora del envío desde CND',
        widget=forms.TextInput(
            attrs={'class': 'form-control',}
        )
    )
    recibido_vrd = forms.DateTimeField(
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    def clean_recibido_vrd(self):
        recv = self.cleaned_data['recibido_vrd']
        send = self.cleaned_data['envio_cnd']
        if send.date() >= recv.date():
            raise forms.ValidationError('La fecha de Envío de CND es posterior a la recepción en  VRD')
        if recv.date() >= dt.date.today():
            raise forms.ValidationError('La fecha de recepción es muy reciente')
        return recv
