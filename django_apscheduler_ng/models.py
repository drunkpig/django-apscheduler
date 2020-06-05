from apscheduler.events import EVENT_JOB_SUBMITTED, EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED, \
    EVENT_JOB_MAX_INSTANCES
from django.db import models
from django.utils.safestring import mark_safe
import datetime

# Create your models here.
class DjangoJob(models.Model):
    """
    定时任务执行情况
    """
    id = models.CharField(max_length=64, primary_key=True)
    job_name = models.CharField(max_length=128)  # 任务名字
    job_state = models.BinaryField()
    description = models.TextField(blank=True)  # job作用描述
    next_run_time = models.DateTimeField(blank=False)  # job开始时间
    gmt_update = models.DateTimeField(auto_now=True)  # 最后更新时间
    gmt_created = models.DateTimeField(auto_now_add=True)  # 创建时间

    class Meta:
        ordering = ('next_run_time', )


class JobExecHistory(models.Model):
    """
    定时任务执行情况
    """
    RUNNING = "Running"
    MAX_INSTANCES = u"Max instances reached!"
    MISSED = u"Missed!"
    ERROR = u"Error!"
    SUCCESS = u"Success"

    _STATUS = {
            str(EVENT_JOB_SUBMITTED): RUNNING,
            str(EVENT_JOB_EXECUTED): SUCCESS,
                str(EVENT_JOB_ERROR):  ERROR,
            str(EVENT_JOB_MISSED):  MISSED,
            str(EVENT_JOB_MAX_INSTANCES):  MAX_INSTANCES
    }

    id = models.AutoField(primary_key=True)
    job = models.ForeignKey(DjangoJob, on_delete=models.CASCADE)
    job_name = models.CharField(max_length=128, verbose_name="任务名称")  # 任务名字
    status = models.CharField(max_length=50, choices=[
        [v, k]
        for v, k in _STATUS.items()
    ])
    job_instance_id = models.CharField(max_length=64, unique=True)  # job实例id
    start_tm = models.DateTimeField(auto_now_add=True)  # job开始时间
    end_tm = models.DateTimeField(auto_now=True)  # 结束（成功|失败)时间
    trace_message = models.TextField(blank=True, verbose_name="追踪日志") # 错误记录等

    def html_status(self):
        m = {
            self.RUNNING: "blue",
            self.MAX_INSTANCES: "yellow",
            self.MISSED: "yellow",
            self.ERROR: "red",
            self.SUCCESS: "green"
        }

        return mark_safe("<p style=\"color: {}\">{}</p>".format(
            m[self._STATUS[self.status]],
            self._STATUS[self.status]
        ))

    def duration(self):
        """
        任务持续时长
        :return:
        """
        delta = self.end_tm-self.start_tm
        if delta < datetime.timedelta(milliseconds=0):
            delta = "00:00:00"
        return str(delta)

    class Meta:
        ordering = ('-start_tm', )