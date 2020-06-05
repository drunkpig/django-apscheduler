import logging
import pickle
from apscheduler.job import Job
from apscheduler.jobstores.base import BaseJobStore, JobLookupError

from django.core.exceptions import ObjectDoesNotExist
from django_apscheduler_ng.models import DjangoJob

LOGGER = logging.getLogger("django_apscheduler")


class DjangoJobStore(BaseJobStore):
    """
    Stores jobs in a Django database.
    :param int pickle_protocol: pickle protocol level to use (for serialization), defaults to the
        highest available
    """

    def __init__(self, pickle_protocol=pickle.HIGHEST_PROTOCOL):
        super(DjangoJobStore, self).__init__()
        self.pickle_protocol = pickle_protocol

    def lookup_job(self, job_id):
        LOGGER.debug("Lookup for a job %s", job_id)
        try:
            job_state = DjangoJob.objects.get(name=job_id).job_state
        except DjangoJob.DoesNotExist as e:
            LOGGER.exception(e)
            return None
        r = self._reconstitute_job(job_state) if job_state else None
        LOGGER.debug("Got %s", r)
        return r

    def get_due_jobs(self, now):
        LOGGER.debug("get_due_jobs for time=%s", now)
        try:
            out = self._get_jobs(next_run_time__lte=now)
            LOGGER.debug("Got %s", out)
            return out
        except Exception as e:
            LOGGER.exception("Exception during getting jobs %s", e)
            return []

    def get_next_run_time(self):
        try:
            return  DjangoJob.objects.filter(next_run_time__isnull=False).earliest('next_run_time').next_run_time
        except ObjectDoesNotExist:  # no active jobs
            return None
        except:
            LOGGER.exception("Exception during get_next_run_time for jobs")

    def get_all_jobs(self):
        jobs = self._get_jobs()
        self._fix_paused_jobs_sorting(jobs)
        return jobs

    def add_job(self, job):
        dbJob, created = DjangoJob.objects.get_or_create(
            defaults=dict(
                next_run_time=job.next_run_time,
                job_state=pickle.dumps(job.__getstate__(), self.pickle_protocol)
            ),
            id=job.id,
            job_name=job.name,
        )

        if not created:
            LOGGER.warning("Job with name %s already in jobstore, job_id=%s. I'll refresh it", job.name, job.id)
            dbJob.next_run_time = job.next_run_time
            dbJob.job_state = pickle.dumps(job.__getstate__(), self.pickle_protocol)
            dbJob.save()

    def update_job(self, job):
        updated = DjangoJob.objects.filter(id=job.id).update(
            next_run_time=job.next_run_time,
            job_state=pickle.dumps(job.__getstate__(), self.pickle_protocol)
        )

        LOGGER.debug(
            "Update job %s: next_run_time=%s, job_state=%s",
            job,
            job.next_run_time,
            job.__getstate__()

        )

        if updated == 0:
            LOGGER.info("Job with id %s not found", job.id)
            raise JobLookupError(job.id)

    def remove_job(self, job_id):
        qs = DjangoJob.objects.filter(id=job_id)
        if not qs.exists():
            LOGGER.warning("Job with id %s not found. Can't remove job.", job_id)
        qs.delete()

    def remove_all_jobs(self):
        DjangoJob.objects.all().delete()

    def shutdown(self):
        self.remove_all_jobs()

    def _reconstitute_job(self, job_state):
        job_state = pickle.loads(job_state)
        job_state['jobstore'] = self
        job = Job.__new__(Job)
        job.__setstate__(job_state)
        job._scheduler = self._scheduler
        job._jobstore_alias = self._alias
        return job

    def _get_jobs(self, **filters):
        job_states = DjangoJob.objects.filter(**filters).values_list('id', 'job_state')
        jobs = []
        failed_job_ids = set()
        for job_id, job_state in job_states:
            try:
                jobs.append(self._reconstitute_job(job_state))
            except:
                self._logger.exception('Unable to restore job "%s" -- removing it', job_id)
                failed_job_ids.add(job_id)

        # Remove all the jobs we failed to restore
        if failed_job_ids:
            LOGGER.warning("Remove bad jobs: %s", failed_job_ids)
            DjangoJob.objects.filter(id__in=failed_job_ids).delete()

        def map_jobs(job):
            job.next_run_time = job.next_run_time
            return job

        return list(map(map_jobs, jobs))
