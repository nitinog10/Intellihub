import azure.functions as func

from closedloop_os.api import app as fastapi_app
from closedloop_os.pipeline import process_raw_event_message

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.FUNCTION)


@app.retry(strategy="fixedDelay", max_retry_count="5", delay_interval="00:00:10")
@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="%SERVICE_BUS_QUEUE_NAME%",
    connection="SERVICE_BUS_CONNECTION_STRING",
)
def classify_raw_event(msg: func.ServiceBusMessage) -> None:
    process_raw_event_message(msg.get_body())
