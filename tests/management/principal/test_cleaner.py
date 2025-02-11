#
# Copyright 2019 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Test the principal cleaner."""
from unittest.mock import Mock, patch

from rest_framework import status
from tenant_schemas.utils import tenant_context

from management.group.model import Group
from management.principal.cleaner import clean_tenant_principals
from management.principal.model import Principal
from tests.identity_request import IdentityRequest

from api.models import Tenant


class PrincipalCleanerTests(IdentityRequest):
    """Test the principal cleaner functions."""

    def setUp(self):
        """Set up the principal cleaner tests."""
        super().setUp()
        with tenant_context(self.tenant):
            self.group = Group(name="groupA", tenant=self.tenant)
            self.group.save()

    def test_principal_cleanup_none(self):
        """Test that we can run a principal clean up on a tenant with no principals."""
        try:
            clean_tenant_principals(self.tenant)
        except Exception:
            self.fail(msg="clean_tenant_principals encountered an exception")
        with tenant_context(self.tenant):
            self.assertEqual(Principal.objects.count(), 0)

    @patch(
        "management.principal.proxy.PrincipalProxy._request_principals",
        return_value={"status_code": status.HTTP_200_OK, "data": []},
    )
    def test_principal_cleanup_skip_cross_account_principals(self, mock_request):
        """Test that principal clean up on a tenant will skip cross account principals."""
        with tenant_context(self.tenant):
            Principal.objects.create(username="user1", tenant=self.tenant)
            Principal.objects.create(username="CAR", cross_account=True, tenant=self.tenant)
            self.assertEqual(Principal.objects.count(), 2)

        try:
            clean_tenant_principals(self.tenant)
        except Exception:
            self.fail(msg="clean_tenant_principals encountered an exception")
        with tenant_context(self.tenant):
            self.assertEqual(Principal.objects.count(), 1)

    @patch(
        "management.principal.proxy.PrincipalProxy._request_principals",
        return_value={"status_code": status.HTTP_200_OK, "data": []},
    )
    def test_principal_cleanup_principal_in_group(self, mock_request):
        """Test that we can run a principal clean up on a tenant with a principal in a group."""
        with tenant_context(self.tenant):
            self.principal = Principal(username="user1", tenant=self.tenant)
            self.principal.save()
            self.group.principals.add(self.principal)
            self.group.save()
        try:
            clean_tenant_principals(self.tenant)
        except Exception:
            self.fail(msg="clean_tenant_principals encountered an exception")
        with tenant_context(self.tenant):
            self.assertEqual(Principal.objects.count(), 0)

    @patch(
        "management.principal.proxy.PrincipalProxy._request_principals",
        return_value={"status_code": status.HTTP_200_OK, "data": []},
    )
    def test_principal_cleanup_principal_not_in_group(self, mock_request):
        """Test that we can run a principal clean up on a tenant with a principal not in a group."""
        with tenant_context(self.tenant):
            self.principal = Principal(username="user1", tenant=self.tenant)
            self.principal.save()
        try:
            clean_tenant_principals(self.tenant)
        except Exception:
            self.fail(msg="clean_tenant_principals encountered an exception")
        with tenant_context(self.tenant):
            self.assertEqual(Principal.objects.count(), 0)

    @patch(
        "management.principal.proxy.PrincipalProxy._request_principals",
        return_value={"status_code": status.HTTP_200_OK, "data": [{"username": "user1"}]},
    )
    def test_principal_cleanup_principal_exists(self, mock_request):
        """Test that we can run a principal clean up on a tenant with an existing principal."""
        with tenant_context(self.tenant):
            self.principal = Principal(username="user1", tenant=self.tenant)
            self.principal.save()
        try:
            clean_tenant_principals(self.tenant)
        except Exception:
            self.fail(msg="clean_tenant_principals encountered an exception")
        with tenant_context(self.tenant):
            self.assertEqual(Principal.objects.count(), 1)

    @patch(
        "management.principal.proxy.PrincipalProxy._request_principals",
        return_value={"status_code": status.HTTP_504_GATEWAY_TIMEOUT},
    )
    def test_principal_cleanup_principal_error(self, mock_request):
        """Test that we can handle a principal clean up with an unexpected error from proxy."""
        with tenant_context(self.tenant):
            self.principal = Principal(username="user1", tenant=self.tenant)
            self.principal.save()
        try:
            clean_tenant_principals(self.tenant)
        except Exception:
            self.fail(msg="clean_tenant_principals encountered an exception")
        with tenant_context(self.tenant):
            self.assertEqual(Principal.objects.count(), 1)

    @patch(
        "management.principal.proxy.PrincipalProxy._request_principals",
        return_value={"status_code": status.HTTP_200_OK, "data": []},
    )
    def test_principal_cleanup_principals_in_public_schema(self, mock_request):
        """Test that we can run a principal clean up on a tenant with a principal in public schema."""
        public_schema = Tenant.objects.get(schema_name="public")
        with tenant_context(self.tenant):
            Principal.objects.create(username="user1", tenant=self.tenant)
            Principal.objects.create(username="user2", tenant=self.tenant)
        with tenant_context(public_schema):
            Principal.objects.create(username="user1", tenant=self.tenant)
            Principal.objects.create(username="user2", tenant=self.tenant)
        try:
            clean_tenant_principals(self.tenant)
        except Exception:
            self.fail(msg="clean_tenant_principals encountered an exception")
        with tenant_context(self.tenant):
            self.assertEqual(Principal.objects.count(), 0)
        with tenant_context(public_schema):
            self.assertEqual(Principal.objects.count(), 0)
