import azure.functions as func

from closedloop_os.api import app as fastapi_app
from closedloop_os.pipeline import process_raw_event_message
from closedloop_os.messaging import build_publisher
from closedloop_os.persistence import build_repository
from closedloop_os.services import NotionSyncService

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.FUNCTION)


@app.retry(strategy="fixedDelay", max_retry_count="5", delay_interval="00:00:10")
@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="%SERVICE_BUS_QUEUE_NAME%",
    connection="SERVICE_BUS_CONNECTION_STRING",
)
def classify_raw_event(msg: func.ServiceBusMessage) -> None:
    process_raw_event_message(msg.get_body())


@app.schedule(arg_name="timer", schedule="0 */5 * * * *", use_monitor=True)
def sync_notion_pages(timer: func.TimerRequest) -> None:
    service = NotionSyncService(repository=build_repository(), publisher=build_publisher())
    service.sync_updated_pages()
