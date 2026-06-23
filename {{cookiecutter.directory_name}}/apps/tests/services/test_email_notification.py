"""
Unit tests for NotificationEmailService.

Uses the locmem e-mail backend (configured in settings.test), so sent messages
land in ``django.core.mail.outbox`` instead of being delivered.
"""
from django.core import mail
from django.test import TestCase

from apps.core.services.email_notification import NotificationEmailService


class TestNotificationEmailService(TestCase):
    def test_returns_false_when_no_recipients(self):
        service = NotificationEmailService.create(recipients=[], content={'message': 'Hi'}, subject='Subject')

        self.assertFalse(service.send_email())
        self.assertEqual(len(mail.outbox), 0)

    def test_sends_to_single_recipient(self):
        service = NotificationEmailService.create(
            recipients='alice@example.com',
            content={'message': 'Hello Alice'},
            subject='Greetings',
        )

        self.assertTrue(service.send_email())
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['alice@example.com'])
        self.assertEqual(message.subject, 'Greetings')
        self.assertEqual(message.body, 'Hello Alice')

    def test_multiple_recipients_use_bcc(self):
        service = NotificationEmailService.create(
            recipients=['primary@example.com', 'second@example.com', 'third@example.com'],
            content={'message': 'Broadcast'},
            subject='News',
        )

        self.assertTrue(service.send_email())
        message = mail.outbox[0]
        self.assertEqual(message.to, ['primary@example.com'])
        self.assertEqual(message.bcc, ['second@example.com', 'third@example.com'])

    def test_reply_to_header_is_set(self):
        service = NotificationEmailService.create(
            recipients='alice@example.com',
            content={'message': 'Hi'},
            subject='Subject',
            reply='support@example.com',
        )

        self.assertTrue(service.send_email())
        self.assertEqual(mail.outbox[0].extra_headers.get('Reply-To'), 'support@example.com')
