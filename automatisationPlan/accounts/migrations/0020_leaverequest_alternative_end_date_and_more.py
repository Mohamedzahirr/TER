# Generated by Django 5.0.6 on 2024-07-25 12:42

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_alter_notification_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaverequest',
            name='alternative_end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='alternative_start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='TimeClock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clock_in_time', models.DateTimeField(auto_now_add=True)),
                ('clock_out_time', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
