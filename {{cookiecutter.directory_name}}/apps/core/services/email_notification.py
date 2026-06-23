from email.mime.image import MIMEImage
from typing import List, Union

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.utils.translation import gettext as _


class NotificationEmailService(object):
    def __init__(
        self,
        content: dict,
        recipients: Union[str, List[str]],
        subject: str,
        sender: str = f'{settings.EMAIL_SENDER_NAME} <{settings.EMAIL_IMAP_USER}>',
        reply: str = None,
        files: list = None,
        template=None,
    ):
        self._content = content
        self._recipients = recipients
        self._subject = subject
        self._sender = sender
        self._template = template
        self._reply = reply
        self._files = files
        self._static_files: list = []

    @classmethod
    def create(
        cls,
        recipients: Union[str, List[str]],
        content: dict,
        subject: str,
        sender: str = f'{settings.EMAIL_SENDER_NAME} <{settings.EMAIL_IMAP_USER}>',
        reply: str = None,
        files: list = None,
        template=None,
    ) -> 'NotificationEmailService':
        return NotificationEmailService(content, recipients, subject, sender, reply, files, template)

    @property
    def message(self) -> dict:
        return self._content

    @property
    def recipients(self) -> Union[str, List[str]]:
        return self._recipients

    def send_email(self) -> bool:
        if not self._recipients:
            return False

        if self._reply:
            email_headers = {'Reply-To': self._reply}
        else:
            email_headers = {}

        content = self._content
        message = content.get('message')

        if message:
            content.pop('message')
        else:
            message = _('blank_message')

        if isinstance(self._recipients, str):
            mail = EmailMultiAlternatives(
                subject=self._subject,
                body=message,
                from_email=self._sender,
                to=[self._recipients],
                headers=email_headers
            )
        else:
            primary_recipient = [self._recipients[0]]
            secondary_recipients = self._recipients[1:]

            mail = EmailMultiAlternatives(
                subject=self._subject,
                body=message,
                from_email=self._sender,
                to=primary_recipient,
                bcc=secondary_recipients,
                headers=email_headers
            )

        if self._template:
            mail_template = get_template(self._template)
            mail_template = mail_template.render(self._content)
            mail.attach_alternative(mail_template, 'text/html')

        if self._files:
            for file in self._files:
                if isinstance(file, MIMEImage):
                    mail.attach(file)
                elif isinstance(file, dict):
                    self._attach_dict_file(file, mail)
                elif isinstance(file, str):
                    mail.attach_file(file)

        return True if mail.send() else False

    @staticmethod
    def _attach_dict_file(dict_file: dict, mail: EmailMultiAlternatives):
        file_path = dict_file['path']
        content_id = dict_file['content_id']

        filename = file_path.rsplit('/', 1)[-1].rsplit('\\', 1)[-1]
        extension = file_path.rsplit('.', 1)[-1]

        with open(file_path, 'rb') as f:
            file_data = f.read()

        static_file = MIMEImage(file_data, extension)
        static_file.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        static_file.add_header('Content-ID', f'<{content_id}>')
        mail.attach(static_file)
