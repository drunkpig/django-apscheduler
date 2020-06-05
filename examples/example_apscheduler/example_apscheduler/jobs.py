import random
import time

from django_apscheduler_ng.scheduler import DjangoBackgroundScheduler
from django_apscheduler_ng.djangojobstores import DjangoJobStore

scheduler = DjangoBackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")


@scheduler.scheduled_job('interval', seconds=10, name='chek_my_payment')
def test_job():
    time.sleep(random.randrange(1, 100, 1)/100.)
    print("I'm a test job!")
    # raise ValueError("Olala!")


scheduler.start()
print("Scheduler started!")
