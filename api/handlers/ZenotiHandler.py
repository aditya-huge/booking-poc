import json
import os
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import requests

DEFAULT_HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "Authorization": f"apikey {os.getenv("ZENOTI_AUTH")}",
}

EXCLUDED_CATEGORIES = ["ADD-ON", "CHARGES & FEES", "CHARGES AND FEES"]
ADDON_CATEGORIES = ["ADD-ON"]


class ZenotiHandler:
    def __init__(self) -> None:
        self.root = os.getenv("ZENOTI_API_URL")

    def get_centers_location(self):
        url = f"{self.root}/centers"
        params = {"catalog_enabled": "false", "expand": "working_hours"}
        response = requests.get(url, headers=DEFAULT_HEADERS, params=params)
        data = response.json()

        return data["centers"] or []

    def get_center_information(self, id: str):
        url = f"{self.root}/Centers/{id}"
        response = requests.get(url, headers=DEFAULT_HEADERS)

        return response.json() or {}

    def get_center_categories(self, center_id: str, category_id=None):
        url = f"{self.root}/centers/{center_id}/categories"
        params = {"page": 1, "type": 1, "size": 10}
        response = requests.get(url, headers=DEFAULT_HEADERS, params=params)
        data = response.json()

        return [
            {**item, "active": item["id"] == category_id}
            for item in data.get("categories", [])
            if item["name"].upper() not in EXCLUDED_CATEGORIES
        ]

    def get_center_addons(self, center_id: str):
        url = f"{self.root}/centers/{center_id}/categories"
        params = {"page": 1, "type": 1, "size": 20}
        response = requests.get(url, headers=DEFAULT_HEADERS, params=params)
        data = response.json()

        addons = [
            item
            for item in data.get("categories", [])
            if item["name"].upper() in ADDON_CATEGORIES
        ]

        addons_id = addons[0].get("id", None)
        services = self.get_center_services(center_id=center_id, category_id=addons_id)

        return {"suggested": services[:4], "all": services[4:]}

    def get_center_category(self, center_id: str, category_id: Optional[str]):
        if not center_id or not category_id:
            return {}

        url = f"{self.root}/Centers/{center_id}/categories/{category_id}"
        response = requests.get(url, headers=DEFAULT_HEADERS)

        return response.json() or {}

    def get_center_services(self, center_id: str, category_id: str):
        url = f"{self.root}/Centers/{center_id}/services"
        params = {
            "page": 1,
            "size": 10,
        }

        if category_id:
            params["category_id"] = category_id

        response = requests.get(url, headers=DEFAULT_HEADERS, params=params)
        data = response.json()

        return data.get("services", [])

    def get_center_service(self, center_id: str, service_id: Optional[str]):
        if not center_id or not service_id:
            return {}

        url = f"{self.root}/centers/{center_id}/services/{service_id}"
        response = requests.get(url, headers=DEFAULT_HEADERS)

        return response.json() or {}

    def get_center_therapists(self, center_id: str):
        if not center_id:
            return []

        url = f"{self.root}/Centers/{center_id}/therapists"
        response = requests.get(url, headers=DEFAULT_HEADERS)
        data = response.json()

        return data.get("therapists", [])

    def get_center_therapist(
        self, therapists: list[Dict[str, Any]], therapist_id: Optional[str]
    ):
        if not therapists or not therapist_id:
            return {}

        filtered_therapist = [
            therapist for therapist in therapists if therapist["id"] == therapist_id
        ]

        return filtered_therapist[0]

    def get_service_schedule(
        self,
        center_id: str,
        guest: Dict[str, Any],
        service_id: str,
        therapist_id: Optional[str],
    ):
        number_of_days = 10
        schedule_list = []
        start_date = datetime.now().date()

        for i in range(number_of_days):
            current_date = start_date + timedelta(days=i)
            booking_service = self._create_booking_service(
                date=current_date.strftime("%Y-%m-%d"),
                center_id=center_id,
                service_id=service_id,
                guest_id=guest["id"],
                therapist_id=therapist_id,
            )
            schedule: Dict[str, Any] = {
                "center_id": center_id,
                "date": current_date.isoformat(),
                "guest_id": guest["id"],
                "service_id": service_id,
                "booking_id": booking_service["id"],
                "slots": self._get_booking_service_slots(
                    booking_service_id=booking_service["id"]
                ),
            }

            schedule_list.append(schedule)

        return schedule_list

    def create_center_guest(self, center_id: str):
        url = f"{self.root}/guests"
        payload = {
            "center_id": center_id,
            "personal_info": {
                "first_name": "Dummy",
                "last_name": "User",
                "gender": "1",
                "email": "ak@ak.com",
                "mobile_phone": {"country_code": 225, "number": "2406886482"},
            },
            "address_info": {
                "address_1": "123 st",
                "city": "arlington",
                "country_id": 225,
                "state_id": 81,
                "zip_code": "22207",
            },
        }
        response = requests.post(url, json=payload, headers=DEFAULT_HEADERS)

        return response.json()

    def _create_booking_service(
        self,
        center_id: str,
        date: str,
        guest_id: str,
        service_id: str,
        therapist_id: Optional[str],
    ):
        url = f"{self.root}/bookings"
        payload = {
            "center_id": center_id,
            "date": date,
            "is_only_catalog_employees": "false",
            "guests": [{"id": guest_id, "items": [{"item": {"id": service_id}}]}],
        }

        # TODO: Add the therapist id if any

        response = requests.post(url, headers=DEFAULT_HEADERS, data=json.dumps(payload))
        booking_service = response.json()

        return booking_service

    def _get_booking_service_slots(self, booking_service_id: str):
        url = f"{self.root}/bookings/{booking_service_id}/slots"
        response = requests.get(url, headers=DEFAULT_HEADERS)

        return response.json().get("slots", [])
