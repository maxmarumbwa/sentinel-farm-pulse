
from django.apps import AppConfig
from django.core.management import call_command
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

class FieldsAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.fields_admin'

    def ready(self):
        # Only start the scheduler in the main process (not during migrations or tests)
        import os
        if os.environ.get('RUN_MAIN') or not os.environ.get('DJANGO_AUTORELOAD'):
            self.start_scheduler()

    def start_scheduler(self):
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            
            def run_backfill_job():
                """Runs the backfill command for the last 3 days up to today."""
                try:
                    end_date = date.today().strftime('%Y-%m-%d')
                    start_date = (date.today() - timedelta(days=3)).strftime('%Y-%m-%d')
                    
                    logger.info(f"🔄 Triggering daily NDVI backfill from {start_date} to {end_date}")
                    
                    # THIS RUNS YOUR EXISTING MANAGEMENT COMMAND
                    call_command('backfill_ndvi', start_date=start_date, end_date=end_date)
                    
                    logger.info("✅ Daily NDVI backfill completed successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to run NDVI backfill: {e}")

            # Create the scheduler
            scheduler = BackgroundScheduler()
            
            # Schedule it to run every day at 9:00 PM GMT+2 (19:00 UTC)
            scheduler.add_job(
                run_backfill_job,
                trigger=CronTrigger(hour=22, minute=47),  # 19:00 UTC = 21:00 GMT+2
                #trigger='interval', seconds=10,
                id='daily_ndvi_backfill',
                replace_existing=True
            )
            
            scheduler.start()
            logger.info("✅ Daily NDVI backfill scheduler started at 21:00 GMT+2")
            
        except Exception as e:
            logger.error(f"❌ Failed to start APScheduler: {e}")