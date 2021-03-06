import base64
import sys

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.test import override_settings
from django.test.testcases import SimpleTestCase

from sendgrid_backend.mail import SendgridBackend

if sys.version_info >= (3.0, 0.0, ):
    from email.mime.image import MIMEImage
else:
    from email.MIMEImage import MIMEImage


class TestMailGeneration(SimpleTestCase):

    # Any assertDictEqual failures will show the entire diff instead of just a snippet
    maxDiff = None

    @classmethod
    def setUpClass(self):
        super(TestMailGeneration, self).setUpClass()
        with override_settings(EMAIL_BACKEND="sendgrid_backend.SendgridBackend",
                               SENDGRID_API_KEY="DUMMY_API_KEY"):
            self.backend = SendgridBackend()

    def test_EmailMessage(self):
        msg = EmailMessage(
            subject="Hello, World!",
            body="Hello, World!",
            from_email="Sam Smith <sam.smith@example.com>",
            to=["John Doe <john.doe@example.com>", "jane.doe@example.com"],
            cc=["Stephanie Smith <stephanie.smith@example.com>"],
            bcc=["Sarah Smith <sarah.smith@example.com>"],
            reply_to=["Sam Smith <sam.smith@example.com>"],
        )

        result = self.backend._build_sg_mail(msg)
        expected = {
            "personalizations": [{
                "to": [{
                    "email": "john.doe@example.com",
                    "name": "John Doe"
                }, {
                    "email": "jane.doe@example.com",
                }],
                "cc": [{
                    "email": "stephanie.smith@example.com",
                    "name": "Stephanie Smith"
                }],
                "bcc": [{
                    "email": "sarah.smith@example.com",
                    "name": "Sarah Smith"
                }],
                "subject": "Hello, World!"
            }],
            "from": {
                "email": "sam.smith@example.com",
                "name": "Sam Smith"
            },
            "mail_settings": {
                "sandbox_mode": {
                    "enable": False
                }
            },
            "reply_to": {
                "email": "sam.smith@example.com",
                "name": "Sam Smith"
            },
            "subject": "Hello, World!",
            "tracking_settings": {"open_tracking": {"enable": True}},
            "content": [{
                "type": "text/plain",
                "value": "Hello, World!"
            }]
        }

        self.assertDictEqual(result, expected)

    def test_EmailMessage_attributes(self):
        """Test that send_at and categories attributes are correctly written through to output."""
        msg = EmailMessage(
            subject="Hello, World!",
            body="Hello, World!",
            from_email="Sam Smith <sam.smith@example.com>",
            to=["John Doe <john.doe@example.com>", "jane.doe@example.com"],
        )

        # Set new attributes as message property
        msg.send_at = 1518108670
        msg.categories = ['mammal', 'dog']

        result = self.backend._build_sg_mail(msg)
        expected = {
            "personalizations": [{
                "to": [{
                    "email": "john.doe@example.com",
                    "name": "John Doe"
                }, {
                    "email": "jane.doe@example.com",
                }],
                "subject": "Hello, World!",
                "send_at": 1518108670,
            }],
            "from": {
                "email": "sam.smith@example.com",
                "name": "Sam Smith"
            },
            "mail_settings": {
                "sandbox_mode": {
                    "enable": False
                }
            },
            "subject": "Hello, World!",
            "tracking_settings": {"open_tracking": {"enable": True}},
            "content": [{
                "type": "text/plain",
                "value": "Hello, World!"
            }],
            "categories": ['mammal', 'dog'],
        }

        self.assertDictEqual(result, expected)

    def test_EmailMultiAlternatives(self):
        msg = EmailMultiAlternatives(
            subject="Hello, World!",
            body=" ",
            from_email="Sam Smith <sam.smith@example.com>",
            to=["John Doe <john.doe@example.com>", "jane.doe@example.com"],
            cc=["Stephanie Smith <stephanie.smith@example.com>"],
            bcc=["Sarah Smith <sarah.smith@example.com>"],
            reply_to=["Sam Smith <sam.smith@example.com>"],
        )

        msg.attach_alternative("<body<div>Hello World!</div></body>", "text/html")

        # Test CSV attachment
        msg.attach("file.csv", "1,2,3,4", "text/csv")
        result = self.backend._build_sg_mail(msg)
        expected = {
            "personalizations": [{
                "to": [{
                    "email": "john.doe@example.com",
                    "name": "John Doe"
                }, {
                    "email": "jane.doe@example.com",
                }],
                "cc": [{
                    "email": "stephanie.smith@example.com",
                    "name": "Stephanie Smith"
                }],
                "bcc": [{
                    "email": "sarah.smith@example.com",
                    "name": "Sarah Smith"
                }],
                "subject": "Hello, World!"
            }],
            "from": {
                "email": "sam.smith@example.com",
                "name": "Sam Smith"
            },
            "mail_settings": {
                "sandbox_mode": {
                    "enable": False
                }
            },
            "reply_to": {
                "email": "sam.smith@example.com",
                "name": "Sam Smith"
            },
            "subject": "Hello, World!",
            "tracking_settings": {"open_tracking": {"enable": True}},
            "attachments": [{
                "content": "MSwyLDMsNA==",
                "filename": "file.csv",
                "type": "text/csv"
            }],
            "content": [{
                "type": "text/plain",
                "value": " ",
            }, {
                "type": "text/html",
                "value": "<body<div>Hello World!</div></body>",
            }]
        }

        self.assertDictEqual(result, expected)

    def test_reply_to(self):
        kwargs = {
            "subject": "Hello, World!",
            "body": "Hello, World!",
            "from_email": "Sam Smith <sam.smith@example.com>",
            "to": ["John Doe <john.doe@example.com>"],
            "reply_to": ["Sam Smith <sam.smith@example.com>"],
            "headers": {"Reply-To": "Stephanie Smith <stephanie.smith@example.com>"}
        }

        # Test different values in Reply-To header and reply_to prop
        msg = EmailMessage(**kwargs)
        with self.assertRaises(ValueError):
            self.backend._build_sg_mail(msg)

        # Test different names (but same email) in Reply-To header and reply_to prop
        kwargs["headers"] = {"Reply-To": "Bad Name <sam.smith@example.com>"}
        msg = EmailMessage(**kwargs)
        with self.assertRaises(ValueError):
            self.backend._build_sg_mail(msg)

        # Test same name/email in both Reply-To header and reply_to prop
        kwargs["headers"] = {"Reply-To": "Sam Smith <sam.smith@example.com>"}
        msg = EmailMessage(**kwargs)
        result = self.backend._build_sg_mail(msg)
        self.assertDictEqual(result["reply_to"], {"email": "sam.smith@example.com", "name": "Sam Smith"})

    def test_mime(self):
        msg = EmailMultiAlternatives(
            subject="Hello, World!",
            body=" ",
            from_email="Sam Smith <sam.smith@example.com>",
            to=["John Doe <john.doe@example.com>", "jane.doe@example.com"],
        )

        content = '<body><img src="cid:linux_penguin" /></body>'
        msg.attach_alternative(content, "text/html")
        with open("test/linux-penguin.png", "rb") as f:
            img = MIMEImage(f.read())
            img.add_header("Content-ID", "<linux_penguin>")
            msg.attach(img)

        result = self.backend._build_sg_mail(msg)
        self.assertEqual(len(result["content"]), 2)
        self.assertDictEqual(result["content"][0], {"type": "text/plain", "value": " "})
        self.assertDictEqual(result["content"][1], {"type": "text/html", "value": content})
        self.assertEqual(len(result["attachments"]), 1)
        self.assertEqual(result["attachments"][0]["content_id"], "linux_penguin")

        with open("test/linux-penguin.png", "rb") as f:
            if sys.version_info >= (3.0, 0.0, ):
                self.assertEqual(bytearray(result["attachments"][0]["content"], "utf-8"), base64.b64encode(f.read()))
            else:
                self.assertEqual(result["attachments"][0]["content"], base64.b64encode(f.read()))
        self.assertEqual(result["attachments"][0]["type"], "image/png")

    def test_templating(self):
        msg = EmailMessage(
            subject="Hello, World!",
            body="Hello, World!",
            from_email="Sam Smith <sam.smith@example.com>",
            to=["John Doe <john.doe@example.com>", "jane.doe@example.com"],
        )
        msg.template_id = "test_template"
        result = self.backend._build_sg_mail(msg)

        self.assertIn("template_id", result)
        self.assertEquals(result["template_id"], "test_template")

    def test_asm(self):
        msg = EmailMessage(
            subject="Hello, World!",
            body="Hello, World!",
            from_email="Sam Smith <sam.smith@example.com>",
            to=["John Doe <john.doe@example.com>", "jane.doe@example.com"],
        )
        msg.asm = {"group_id": 1}
        result = self.backend._build_sg_mail(msg)

        self.assertIn("asm", result)
        self.assertIn("group_id", result["asm"])

        del msg.asm["group_id"]
        with self.assertRaises(KeyError):
            self.backend._build_sg_mail(msg)

        msg.asm = {"group_id": 1, "groups_to_display": [2, 3, 4], "bad_key": None}
        result = self.backend._build_sg_mail(msg)

        self.assertIn("asm", result)
        self.assertIn("group_id", result["asm"])
        self.assertIn("groups_to_display", result["asm"])

    """
    todo: Implement these
    def test_attachments(self):
        pass

    def test_headers(self):
        pass

    """
