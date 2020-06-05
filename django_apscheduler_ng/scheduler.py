from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.util import undefined
import hashlib
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_ADDED, EVENT_JOB_MISSED, \
    JobExecutionEvent, EVENT_JOB_SUBMITTED, EVENT_JOB_MAX_INSTANCES
from logging import getLogger
from datetime import datetime

from django.db import IntegrityError

from django_apscheduler_ng.models import JobExecHistory, DjangoJob

logger = getLogger("job_scheduler")


class DjangoBackgroundScheduler(BackgroundScheduler):
    def start(self, *args, **kwargs):
        self._register_listener()
        super().start(*args, **kwargs)

    def scheduled_job(self, trigger, args=None, kwargs=None, id=None, name=None,
                      misfire_grace_time=undefined, coalesce=undefined, max_instances=undefined,
                      next_run_time=undefined, jobstore='default', executor='default',
                      **trigger_args):
        """
        add default id = md5(name) if id is None
        :param trigger:
        :param args:
        :param kwargs:
        :param id:
        :param name:
        :param misfire_grace_time:
        :param coalesce:
        :param max_instances:
        :param next_run_time:
        :param jobstore:
        :param executor:
        :param trigger_args:
        :return:
        """

        if id is None and name:
            id = hashlib.md5(name.encode()).hexdigest()
        else:
            raise Exception("job name should not null")
        return BaseScheduler.scheduled_job(self, trigger, args=args, kwargs=kwargs, id=id, name=name,
                      misfire_grace_time=misfire_grace_time, coalesce=coalesce, max_instances=max_instances,
                      next_run_time=next_run_time, jobstore=jobstore, executor=executor, **trigger_args)

    def _register_listener(self):
        event = EVENT_JOB_SUBMITTED | EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED |EVENT_JOB_MAX_INSTANCES
        self.add_listener(self._job_listener, event)

    @staticmethod
    def _job_listener(event):
        def update_or_create(job_name, event, exception='-'):
            """

            :param job_name:
            :param event:
            :return:
            """

            try:
                JobExecHistory.objects.update_or_create(job_instance_id=event.job_instance_id, job_name=job_name, \
                                                 status=event.code, job_id=event.job_id, trace_message=exception,\
                                                        end_tm=event.event_tm)
            except IntegrityError as e:
                JobExecHistory.objects.filter(job_instance_id=event.job_instance_id).update(status=event.code,
                                                                                            trace_message=exception,
                                                                                            end_tm=event.event_tm)

        job = DjangoJob.objects.get(id=event.job_id) # TODO 多个的时候，记录错误
        if not job:
            logger.error(f"Job id={event.job_id} not found when update job instance status")
            return

        if isinstance(event, JobExecutionEvent):
            if event.exception:
                logger.info(f'eventcode={event.code}, job_instance_id={event.job_instance_id} crashed :(')
                update_or_create(job.job_name, event, event.exception)
                return
            else:
                logger.info(f'eventcode={event.code}, job_instance_id={event.job_instance_id} worked :)')
                update_or_create(job.job_name, event)
        else:  # jobs are executed in a seperate thread, so the result event my arrive earlier than job submit event
            if event.code==EVENT_JOB_SUBMITTED:
                logger.info(f"eventcode={event.code}, job_instance_id={event.job_instance_id}")
                try:
                    JobExecHistory.objects.create(job_instance_id=event.job_instance_id, job_name=job.job_name, \
                                                        job_id=event.job_id, status=event.code, start_tm=event.event_tm)
                except:
                    JobExecHistory.objects.filter(job_instance_id=event.job_instance_id).update(start_tm=event.event_tm)
            else:
                logger.info(f"eventcode={event.code}, job_instance_id={event.job_instance_id}")
                update_or_create(job.job_name, event)
