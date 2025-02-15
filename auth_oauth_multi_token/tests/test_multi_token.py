# Copyright 2017 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import json

from odoo import exceptions
from odoo.tests import TransactionCase


class TestMultiToken(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Remove this variable in v16 and put instead:
        # from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
        DISABLED_MAIL_CONTEXT = {
            "tracking_disable": True,
            "mail_create_nolog": True,
            "mail_create_nosubscribe": True,
            "mail_notrack": True,
            "no_reset_password": True,
        }
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.token_model = cls.env["auth.oauth.multi.token"]
        cls.provider_google = cls.env.ref("auth_oauth.provider_google")
        cls.user_model = cls.env["res.users"].with_context(
            tracking_disable=True, no_reset_password=True
        )
        cls.user = cls.user_model.create(
            {
                "name": "John Doe",
                "login": "johndoe",
                "oauth_uid": "oauth_uid_johndoe",
                "oauth_provider_id": cls.provider_google.id,
            }
        )

    def _fake_params(self, **kw):
        params = {
            "state": json.dumps({"t": "FAKE_TOKEN"}),
            "access_token": "FAKE_ACCESS_TOKEN",
        }
        params.update(kw)
        return params

    def test_no_provider_no_access(self):
        validation = {
            "user_id": "oauth_uid_no_one",
        }
        params = self._fake_params()
        with self.assertRaises(exceptions.AccessDenied):
            self.user_model._auth_oauth_signin(
                self.provider_google.id, validation, params
            )

    def _test_one_token(self):
        validation = {
            "user_id": "oauth_uid_johndoe",
        }
        params = self._fake_params()
        login = self.user_model._auth_oauth_signin(
            self.provider_google.id, validation, params
        )
        self.assertEqual(login, "johndoe")

    def test_access_one_token(self):
        # no token yet
        self.assertFalse(self.user.oauth_access_token_ids)
        self._test_one_token()
        token_count = 1
        self.assertEqual(len(self.user.oauth_access_token_ids), token_count)
        self.assertEqual(
            len(self.token_model._oauth_user_tokens(self.user.id)), token_count
        )

    def test_access_multi_token(self):
        # no token yet
        self.assertFalse(self.user.oauth_access_token_ids)
        # use as many token as max allowed
        for token_count in range(1, self.user.oauth_access_max_token + 1):
            self._test_one_token()
            self.assertEqual(len(self.user.oauth_access_token_ids), token_count)
            self.assertEqual(
                len(self.token_model._oauth_user_tokens(self.user.id)), token_count
            )
        # exceed the number
        self._test_one_token()
        # token count does not exceed max number
        self.assertEqual(
            len(self.user.oauth_access_token_ids), self.user.oauth_access_max_token
        )

    def test_remove_oauth_access_token(self):
        res = self.user._get_session_token_fields()
        self.assertFalse("oauth_access_token" in res)
        self.assertTrue("oauth_master_uuid" in res)

    def test_action_oauth_clear_token(self):
        self.user.action_oauth_clear_token()
        active_token = self.user.oauth_access_token_ids
        self.assertEqual(len(active_token), 0)
