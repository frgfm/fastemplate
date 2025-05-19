# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "locust>=2.37.3",
# ]
# ///

import os

from locust import HttpUser, between, task


class BackendUser(HttpUser):
    wait_time = between(1, 3)  # Users will wait 1-3 seconds between tasks

    def on_start(self):
        """
        This method is called when a Locust user starts.
        We disable SSL certificate verification here because Traefik will be using
        a self-signed certificate for api.docker.localhost in the test environment.
        """
        self.client.verify = False
        response = self.client.post(
            "/api/v1/login/creds",
            name="/api/v1/login/creds",
            data={
                "username": os.getenv("SUPERADMIN_EMAIL"),
                "password": os.getenv("SUPERADMIN_PWD"),
            },
        )
        if response.status_code == 200:
            self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        else:
            raise Exception(f"Failed to authenticate, status: {response.status_code}")

    @task(2)
    def get_docs(self):
        self.client.get("/docs", name="/docs")

    @task(2)
    def authenticate_with_incorrect_credentials(self):
        with self.client.post(
            "/api/v1/login/creds",
            name="/api/v1/login/creds",
            catch_response=True,
            data={"username": "test@test.com", "password": "test"},
        ) as response:
            if response.status_code == 404:
                response.success()
            else:
                response.failure(f"Failed to authenticate, status: {response.status_code}")

    @task(1)
    def read_users(self):
        self.client.get("/api/v1/users", name="/api/v1/users", headers=self.headers)

    @task(4)
    def login_validate_with_token(self):
        self.client.get("/api/v1/login/validate", name="/api/v1/login/validate", headers=self.headers)

    @task(4)
    def login_validate_without_token(self):
        with self.client.get("/api/v1/login/validate", catch_response=True, name="/api/v1/login/validate") as response:
            if response.status_code == 401:
                response.success()
            else:
                response.failure(f"Unexpected status for /api/v1/login/validate: {response.status_code}")
