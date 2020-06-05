import datetime

from django.contrib import admin
from django.db.models import Avg
from django.utils.timezone import now
from .models import DjangoJob, JobExecHistory


@admin.register(DjangoJob)
class DjangoJobAdmin(admin.ModelAdmin):
    list_display = ["id", "job_name", "next_run_time", "avg_duration", "gmt_update", "gmt_created"]
    actions = []

    def next_run_time(self, obj):
        if obj.next_run_time is None:
            return "(paused)"
        return obj.next_run_time

    def avg_duration(self, obj):
        return  0 # TODO


@admin.register(JobExecHistory)
class DjangoJobExecAdmin(admin.ModelAdmin):
    list_display = ["id", "job_name", "job_instance_id",  "html_status", "duration", "start_tm", "end_tm"]
    list_filter = ["job_name",  "status"]

