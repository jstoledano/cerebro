# Generated by Django 2.0.5 on 2018-06-13 20:33

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Remesa',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('remesa', models.CharField(max_length=7)),
                ('inicio', models.DateField()),
                ('fin', models.DateField()),
            ],
        ),
    ]
