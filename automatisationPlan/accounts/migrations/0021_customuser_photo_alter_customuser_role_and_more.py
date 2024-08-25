# Generated by Django 5.0.6 on 2024-08-02 19:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_leaverequest_alternative_end_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='photos/'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(choices=[('employee', 'Employee'), ('team_lead', 'Team Lead')], default='employee', max_length=10),
        ),
        migrations.AlterField(
            model_name='timeclock',
            name='clock_in_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
