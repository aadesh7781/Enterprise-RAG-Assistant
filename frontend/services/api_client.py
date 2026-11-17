
import requests


class APIClient:

    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")
        self.timeout = 90

    def request(self, method, endpoint, token=None, **kwargs):
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})

        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.timeout,
                **kwargs,
            )

            response.raise_for_status()

            if response.status_code == 204 or not response.content:
                return None

            return response.json()

        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code

            try:
                error_data = exc.response.json()
                detail = error_data.get("detail", "Request failed")

                if isinstance(detail, list):
                    detail = "; ".join(
                        str(item.get("msg", item))
                        for item in detail
                    )

            except (ValueError, AttributeError):
                detail = exc.response.text[:500] or "Request failed"

            raise RuntimeError(
                f"HTTP {status_code}: {detail}"
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                "Cannot connect to FastAPI. Check whether the backend is running."
            ) from exc

        except requests.exceptions.Timeout as exc:
            raise RuntimeError(
                f"Request to {endpoint} timed out after "
                f"{self.timeout} seconds."
            ) from exc

        except requests.exceptions.RequestException as exc:
            raise RuntimeError(
                f"API communication error: {exc}"
            ) from exc

        except ValueError as exc:
            raise RuntimeError(
                f"Invalid JSON response from {endpoint}."
            ) from exc

    # AUTHENTICATION

    def login(self, email, password):
        return self.request(
            "POST",
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )

    def get_current_user(self, token):
        return self.request(
            "GET",
            "/api/v1/auth/me",
            token=token,
        )

    # CHAT

    def send_message(
        self,
        token,
        question,
        conversation_id=None,
        top_k=5,
    ):
        payload = {
            "question": question,
            "top_k": top_k,
        }

        if conversation_id:
            payload["conversation_id"] = conversation_id

        return self.request(
            "POST",
            "/api/v1/chat",
            token=token,
            json=payload,
        )

    # CONVERSATIONS

    def get_conversations(self, token):
        return self.request(
            "GET",
            "/api/v1/conversations",
            token=token,
        )

    def get_conversation(self, token, conversation_id):
        return self.request(
            "GET",
            f"/api/v1/conversations/{conversation_id}",
            token=token,
        )

    # KNOWLEDGE BASE

    def get_documents(self, token, department_id=None):
        params = {}

        if department_id:
            params["department_id"] = department_id

        return self.request(
            "GET",
            "/api/v1/documents",
            token=token,
            params=params,
        )

    def upload_document(
        self,
        token,
        file_name,
        file_bytes,
        department_id=None,
    ):
        data = {}

        if department_id:
            data["department_id"] = department_id

        return self.request(
            "POST",
            "/api/v1/documents/upload",
            token=token,
            files={
                "file": (file_name, file_bytes)
            },
            data=data,
        )

    def delete_document(self, token, document_id):
        return self.request(
            "DELETE",
            f"/api/v1/documents/{document_id}",
            token=token,
        )

    # ADMINISTRATION

    def get_all_users(self, token):
        return self.request(
            "GET",
            "/api/v1/admin/users",
            token=token,
        )

    def get_department_users(self, token):
        return self.request(
            "GET",
            "/api/v1/admin/department/users",
            token=token,
        )

    def get_departments(self, token):
        return self.request(
            "GET",
            "/api/v1/admin/departments",
            token=token,
        )

    def create_user(
        self,
        token,
        email,
        full_name,
        password,
        role_name,
        department_id=None,
    ):
        payload = {
            "email": email,
            "full_name": full_name,
            "password": password,
            "role_name": role_name,
            "department_id": department_id,
        }

        return self.request(
            "POST",
            "/api/v1/admin/users",
            token=token,
            json=payload,
        )

    def assign_user_role(self, token, user_id, role_name):
        return self.request(
            "POST",
            f"/api/v1/admin/users/{user_id}/roles",
            token=token,
            json={"role_name": role_name},
        )

    def remove_user_role(self, token, user_id, role_name):
        return self.request(
            "DELETE",
            f"/api/v1/admin/users/{user_id}/roles/{role_name}",
            token=token,
        )

    def assign_user_department(
        self,
        token,
        user_id,
        department_id,
    ):
        return self.request(
            "PUT",
            f"/api/v1/admin/users/{user_id}/department",
            token=token,
            json={"department_id": department_id},
        )
