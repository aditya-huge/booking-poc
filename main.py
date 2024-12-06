from typing import Annotated, Dict, Optional
from dotenv import load_dotenv


load_dotenv()

from urllib.parse import urlencode
from datetime import datetime
from fastapi import FastAPI, Request, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.handlers.ZenotiHandler import ZenotiHandler

origins = ["*"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def dict_to_query_params(value: Dict) -> str:
    print(value)
    if not isinstance(value, Dict):
        return ""
    return urlencode(value)


def iso_date_to_human_readable(iso_date):
    try:
        date_obj = datetime.fromisoformat(iso_date)
        human_readable_date = date_obj.strftime("%B %d, %Y")
        return human_readable_date
    except ValueError:
        return ""


def iso_to_ampm_time(iso_datetime):
    try:
        datetime_obj = datetime.fromisoformat(iso_datetime)
        ampm_time = datetime_obj.strftime("%I:%M %p")
        return ampm_time
    except ValueError:
        return ""


templates = Jinja2Templates(directory="templates")
templates.env.filters["to_query_params"] = dict_to_query_params
templates.env.filters["iso_date_to_human"] = iso_date_to_human_readable
templates.env.filters["iso_to_ampm"] = iso_to_ampm_time


@app.get("/", response_class=HTMLResponse)
async def start(request: Request, zenoti_handler: Annotated[ZenotiHandler, Depends()]):
    context = {"title": "A POC page", "centers": zenoti_handler.get_centers_location()}
    return templates.TemplateResponse(
        request=request, name="index.html", context=context
    )


@app.get("/centers", response_class=HTMLResponse)
async def get_centers_locations(
    request: Request,
):
    context = {"title": "Second step"}
    return templates.TemplateResponse(
        request=request, name="centers.html", context=context
    )


@app.get("/centers/{center_id}")
async def view_center(
    center_id: str,
    request: Request,
    zenoti_handler: Annotated[ZenotiHandler, Depends()],
):
    selected_center = zenoti_handler.get_center_information(center_id)
    categories = zenoti_handler.get_center_categories(center_id)

    context = {"categories": categories, **selected_center}
    return templates.TemplateResponse(
        request=request, name="center.html", context=context
    )


@app.get("/centers/{center_id}/categories/{category_id}")
async def view_center_with_services(
    center_id: str,
    category_id: str,
    request: Request,
    zenoti_handler: Annotated[ZenotiHandler, Depends()],
):
    selected_center = zenoti_handler.get_center_information(center_id)
    categories = zenoti_handler.get_center_categories(center_id)
    services = zenoti_handler.get_center_services(
        center_id=center_id, category_id=category_id
    )

    context = {
        "category_id": category_id,
        "categories": categories,
        "services": services,
        **selected_center,
    }
    return templates.TemplateResponse(
        request=request, name="center.html", context=context
    )


@app.get("/centers/{center_id}/therapists")
async def view_service_providers(
    center_id: str,
    category_id: Optional[str],
    service_id: Optional[str],
    request: Request,
    zenoti_handler: Annotated[ZenotiHandler, Depends()],
):
    center = zenoti_handler.get_center_information(center_id)
    categories = zenoti_handler.get_center_categories(center_id)
    category = zenoti_handler.get_center_category(
        center_id=center_id, category_id=category_id
    )
    addons = zenoti_handler.get_center_addons(center_id=center_id)
    service = zenoti_handler.get_center_service(
        center_id=center_id, service_id=service_id
    )
    therapists = zenoti_handler.get_center_therapists(center_id=center_id)
    context = {
        "categories": categories,
        "category": category,
        "addons": addons,
        "service": service,
        "therapists": therapists,
        **center,
    }

    print(therapists)
    return templates.TemplateResponse(
        request=request, name="center_therapists.html", context=context
    )


@app.get("/centers/{center_id}/schedules")
async def view_center_schedule(
    center_id: str,
    category_id: Optional[str],
    service_id: Optional[str],
    therapist_id: Optional[str],
    request: Request,
    zenoti_handler: Annotated[ZenotiHandler, Depends()],
):
    assert service_id is not None, "The `service_id` query parameter should not be None"

    guest = zenoti_handler.create_center_guest(center_id=center_id)
    center = zenoti_handler.get_center_information(center_id)
    categories = zenoti_handler.get_center_categories(center_id)
    category = zenoti_handler.get_center_category(
        center_id=center_id, category_id=category_id
    )
    addons = zenoti_handler.get_center_addons(center_id=center_id)
    service = zenoti_handler.get_center_service(
        center_id=center_id, service_id=service_id
    )
    therapists = zenoti_handler.get_center_therapists(center_id=center_id)
    therapist = zenoti_handler.get_center_therapist(
        therapists=therapists, therapist_id=therapist_id
    )
    schedule = zenoti_handler.get_service_schedule(
        center_id=center_id,
        therapist_id=therapist_id,
        service_id=service_id,
        guest=guest,
    )
    context = {
        "center": center,
        "categories": categories,
        "category": category,
        "addons": addons,
        "service": service,
        "therapist": therapist,
        "schedule": schedule,
        "guest": guest,
        **center,
    }

    return templates.TemplateResponse(
        request=request, name="center_schedule.html", context=context
    )


@app.get("/centers/{center_id}/invoices")
async def view_invoice(
    center_id: str,
    slot: Optional[str],
    booking_id: Optional[str],
    request: Request,
    zenoti_handler: Annotated[ZenotiHandler, Depends()],
):
    assert slot is not None, "The `slot` query parameter should not be None"
    assert booking_id is not None, "The `booking_id` query parameter should not be None"

    new_invoice = zenoti_handler.reserve_service_booking(
        booking_id=booking_id, slot=slot
    )
    print(new_invoice)
    invoice = zenoti_handler.get_invoice(invoice_id=new_invoice["id"])
    print(invoice)
    center = zenoti_handler.get_center_information(center_id)
    context = {"invoice": invoice, **center}
    return templates.TemplateResponse(
        request=request, name="invoice.html", context=context
    )


@app.post("/invoice/{invoice_id}/apply-code")
async def apply_promo_code(
    invoice_id: str,
    center_id: Annotated[str, Form()],
    promo_code: Annotated[str, Form()],
    request: Request,
    zenoti_handler: Annotated[ZenotiHandler, Depends()],
):
    invoice = zenoti_handler.get_invoice(invoice_id=invoice_id)
    result = zenoti_handler.invoice_apply_promo_code(
        invoice_id=invoice_id, promo_code=promo_code, center_id=center_id
    )
    center = zenoti_handler.get_center_information(center_id)
    context = {
        "promo_applied": result["discount_applied"],
        "invoice": invoice,
        **center,
    }

    return templates.TemplateResponse(
        request=request, name="invoice.html", context=context
    )
