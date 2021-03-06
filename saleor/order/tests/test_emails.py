from unittest import mock

import pytest
from templated_email import get_connection

import saleor.order.emails as emails

from ..utils import add_variant_to_draft_order


def test_collect_data_for_order_confirmation_email(order):
    """Order confirmation email requires extra data, which should be present
    in email's context.
    """
    template = emails.CONFIRM_ORDER_TEMPLATE
    email_data = emails.collect_data_for_email(order.pk, template)
    email_context = email_data["context"]
    assert email_context["order"] == order
    assert "schema_markup" in email_context


def test_collect_data_for_fulfillment_email(fulfilled_order):
    template = emails.CONFIRM_FULFILLMENT_TEMPLATE
    fulfillment = fulfilled_order.fulfillments.first()
    fulfillment_data = emails.collect_data_for_fulfillment_email(
        fulfilled_order.pk, template, fulfillment.pk
    )
    email_context = fulfillment_data["context"]
    assert email_context["fulfillment"] == fulfillment
    email_data = emails.collect_data_for_email(fulfilled_order.pk, template)
    assert all([key in email_context for key, item in email_data["context"].items()])


def test_collect_data_for_email(order):
    template = emails.CONFIRM_PAYMENT_TEMPLATE
    email_data = emails.collect_data_for_email(order.pk, template)
    email_context = email_data["context"]
    # This properties should be present only for order confirmation email
    assert "schema_markup" not in email_context


@mock.patch("saleor.order.emails.send_templated_mail")
def test_send_email_payment_confirmation(mocked_templated_email, order, site_settings):
    template = emails.CONFIRM_PAYMENT_TEMPLATE
    emails.send_payment_confirmation(order.pk)
    email_data = emails.collect_data_for_email(order.pk, template)

    recipients = [order.get_customer_email()]

    expected_call_kwargs = {
        "context": email_data["context"],
        "from_email": site_settings.default_from_email,
        "template_name": template,
    }

    mocked_templated_email.assert_called_once_with(
        recipient_list=recipients, **expected_call_kwargs
    )

    # Render the email to ensure there is no error
    email_connection = get_connection()
    email_connection.get_email_message(to=recipients, **expected_call_kwargs)


@mock.patch("saleor.order.emails.send_templated_mail")
def test_send_staff_emails_without_notification_recipient(
    mocked_templated_email, order, site_settings
):
    emails.send_staff_order_confirmation(order.pk, "http://www.example.com/")
    mocked_templated_email.assert_not_called()


@mock.patch("saleor.order.emails.send_templated_mail")
def test_send_staff_emails(
    mocked_templated_email, order, site_settings, staff_notification_recipient
):
    redirect_url = "http://www.example.com/"
    emails.send_staff_order_confirmation(order.pk, redirect_url)
    email_data = emails.collect_staff_order_notification_data(
        order.pk, emails.STAFF_CONFIRM_ORDER_TEMPLATE, redirect_url
    )

    recipients = [staff_notification_recipient.get_email()]

    expected_call_kwargs = {
        "context": email_data["context"],
        "from_email": site_settings.default_from_email,
        "template_name": emails.STAFF_CONFIRM_ORDER_TEMPLATE,
    }

    mocked_templated_email.assert_called_once_with(
        recipient_list=recipients, **expected_call_kwargs
    )

    # Render the email to ensure there is no error
    email_connection = get_connection()
    email_connection.get_email_message(to=recipients, **expected_call_kwargs)


@mock.patch("saleor.order.emails.send_templated_mail")
def test_send_email_order_confirmation(mocked_templated_email, order, site_settings):
    template = emails.CONFIRM_ORDER_TEMPLATE
    redirect_url = "https://www.example.com"
    emails.send_order_confirmation(order.pk, redirect_url)
    email_data = emails.collect_data_for_email(order.pk, template, redirect_url)

    recipients = [order.get_customer_email()]

    expected_call_kwargs = {
        "context": email_data["context"],
        "from_email": site_settings.default_from_email,
        "template_name": template,
    }

    mocked_templated_email.assert_called_once_with(
        recipient_list=recipients, **expected_call_kwargs
    )

    # Render the email to ensure there is no error
    email_connection = get_connection()
    email_connection.get_email_message(to=recipients, **expected_call_kwargs)


@mock.patch("saleor.order.emails.send_templated_mail")
def test_send_confirmation_emails_without_addresses_for_payment(
    mocked_templated_email, order, site_settings, digital_content
):

    assert not order.lines.count()

    template = emails.CONFIRM_PAYMENT_TEMPLATE
    add_variant_to_draft_order(order, digital_content.product_variant, quantity=1)
    order.shipping_address = None
    order.shipping_method = None
    order.billing_address = None
    order.save(update_fields=["shipping_address", "shipping_method", "billing_address"])

    emails.send_payment_confirmation(order.pk)
    email_data = emails.collect_data_for_email(order.pk, template)

    recipients = [order.get_customer_email()]

    expected_call_kwargs = {
        "context": email_data["context"],
        "from_email": site_settings.default_from_email,
        "template_name": template,
    }

    mocked_templated_email.assert_called_once_with(
        recipient_list=recipients, **expected_call_kwargs
    )

    # Render the email to ensure there is no error
    email_connection = get_connection()
    email_connection.get_email_message(to=recipients, **expected_call_kwargs)


@mock.patch("saleor.order.emails.send_templated_mail")
def test_send_confirmation_emails_without_addresses_for_order(
    mocked_templated_email, order, site_settings, digital_content
):

    assert not order.lines.count()

    template = emails.CONFIRM_ORDER_TEMPLATE
    add_variant_to_draft_order(order, digital_content.product_variant, quantity=1)
    order.shipping_address = None
    order.shipping_method = None
    order.billing_address = None
    order.save(update_fields=["shipping_address", "shipping_method", "billing_address"])

    redirect_url = "https://www.example.com"
    emails.send_order_confirmation(order.pk, redirect_url)
    email_data = emails.collect_data_for_email(order.pk, template, redirect_url)

    recipients = [order.get_customer_email()]

    expected_call_kwargs = {
        "context": email_data["context"],
        "from_email": site_settings.default_from_email,
        "template_name": template,
    }

    mocked_templated_email.assert_called_once_with(
        recipient_list=recipients, **expected_call_kwargs
    )

    # Render the email to ensure there is no error
    email_connection = get_connection()
    email_connection.get_email_message(to=recipients, **expected_call_kwargs)


@pytest.mark.parametrize(
    "send_email,template",
    [
        (
            emails.send_fulfillment_confirmation,
            emails.CONFIRM_FULFILLMENT_TEMPLATE,
        ),  # noqa
        (emails.send_fulfillment_update, emails.UPDATE_FULFILLMENT_TEMPLATE),
    ],
)
@mock.patch("saleor.order.emails.send_templated_mail")
def test_send_fulfillment_emails(
    mocked_templated_email, template, send_email, fulfilled_order, site_settings
):
    fulfillment = fulfilled_order.fulfillments.first()
    send_email(order_pk=fulfilled_order.pk, fulfillment_pk=fulfillment.pk)
    email_data = emails.collect_data_for_fulfillment_email(
        fulfilled_order.pk, template, fulfillment.pk
    )

    recipients = [fulfilled_order.get_customer_email()]

    expected_call_kwargs = {
        "context": email_data["context"],
        "from_email": site_settings.default_from_email,
        "template_name": template,
    }

    mocked_templated_email.assert_called_once_with(
        recipient_list=recipients, **expected_call_kwargs
    )

    # Render the email to ensure there is no error
    email_connection = get_connection()
    email_connection.get_email_message(to=recipients, **expected_call_kwargs)


@pytest.mark.parametrize(
    "send_email,template",
    [
        (
            emails.send_fulfillment_confirmation,
            emails.CONFIRM_FULFILLMENT_TEMPLATE,
        ),  # noqa
        (emails.send_fulfillment_update, emails.UPDATE_FULFILLMENT_TEMPLATE),
    ],
)
@mock.patch("saleor.order.emails.send_templated_mail")
def test_send_fulfillment_emails_with_tracking_number_as_url(
    mocked_templated_email, template, send_email, fulfilled_order, site_settings
):
    fulfillment = fulfilled_order.fulfillments.first()
    fulfillment.tracking_number = "https://www.example.com"
    fulfillment.save()
    assert fulfillment.is_tracking_number_url
    send_email(order_pk=fulfilled_order.pk, fulfillment_pk=fulfillment.pk)
    email_data = emails.collect_data_for_fulfillment_email(
        fulfilled_order.pk, template, fulfillment.pk
    )

    recipients = [fulfilled_order.get_customer_email()]

    expected_call_kwargs = {
        "context": email_data["context"],
        "from_email": site_settings.default_from_email,
        "template_name": template,
    }

    mocked_templated_email.assert_called_once_with(
        recipient_list=recipients, **expected_call_kwargs
    )

    # Render the email to ensure there is no error
    email_connection = get_connection()
    email_connection.get_email_message(to=recipients, **expected_call_kwargs)
