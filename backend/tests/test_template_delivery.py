from datetime import timedelta

from dueflow.application.message_delivery import TemplateConfiguration
from dueflow.application.worker import Worker
from dueflow.infrastructure.db.job_queue import DatabaseJobQueue
from dueflow.infrastructure.messaging.fake import FakeWhatsAppProvider
import pytest


def test_always_mode_uses_template_for_regular_processing(
    client,
    database,
    customer,
) -> None:
    charge = client.post(
        "/charges",
        json={
            "customer_id": customer["id"],
            "description": "Mensalidade de julho",
            "amount": "249.90",
            "due_date": "2026-07-29",
        },
    ).json()
    accepted = client.post(
        f"/charges/{charge['id']}/process",
        json={"reference_date": "2026-07-29"},
    ).json()
    worker = Worker(
        database=database,
        queue=DatabaseJobQueue(database),
        provider=FakeWhatsAppProvider(),
        worker_id="template-default-worker",
        timezone="America/Sao_Paulo",
        poll_interval_seconds=0.01,
        lock_ttl=timedelta(minutes=5),
        template_configuration=TemplateConfiguration(
            mode="always",
            name="dueflow_aviso_cobranca_v1",
            language="pt_BR",
        ),
    )

    assert worker.run_once() is True

    job = client.get(
        f"/processing/jobs/{accepted['job_id']}"
    ).json()
    attempt_id = job["result"]["evaluations"][0]["notification"]["attempt_id"]
    attempt = client.get(f"/notifications/{attempt_id}").json()
    assert attempt["message_format"] == "template"
    assert attempt["template_info"]["name"] == "dueflow_aviso_cobranca_v1"
    assert attempt["template_info"]["parameters"] == [
        customer["name"],
        "Mensalidade de julho",
        "R$ 249,90",
        "29/07/2026",
    ]


def test_template_configuration_rejects_render_when_unavailable() -> None:
    configuration = TemplateConfiguration(name="")

    with pytest.raises(RuntimeError, match="não configurado"):
        configuration.render(customer=None, charge=None)  # type: ignore[arg-type]
