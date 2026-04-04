# -*- coding: utf-8 -*-
"""
Plantillas de Email para Reserfy
Diseño UI/UX moderno estilo SaaS compatible con mobile y todos los clientes de email
"""

import os
import pytz
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SGMail

MAIL_SENDER = os.getenv("MAIL_DEFAULT_SENDER")


# ============================================================================
# PLANTILLA BASE - Estructura común para todos los emails
# ============================================================================

def _get_base_template():
    return '''<!DOCTYPE html>
<html lang="es" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="format-detection" content="telephone=no, address=no, email=no, date=no">
    <title>{{asunto}}</title>
    <style type="text/css">
        body, table, td, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
        table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
        img { -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; }
        body { margin: 0; padding: 0; background-color: #f4f4f5; }
        @media screen and (max-width: 600px) {
            .email-container { width: 100% !important; }
            .header-pad { padding: 25px 15px !important; }
            .body-pad { padding: 20px 15px !important; }
            .header-title { font-size: 20px !important; }
        }
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f4f4f5;">
        <tr>
            <td align="center" style="padding: 20px 10px;">
                <table role="presentation" cellpadding="0" cellspacing="0" width="600" class="email-container" style="max-width: 600px; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    {{contenido}}
                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''


# ============================================================================
# HELPERS - Componentes reutilizables
# ============================================================================

def _header(titulo, subtitulo, color1="#912A5C", color2="#FA8F3E"):
    """Genera el header con gradiente."""
    return f'''
                    <tr>
                        <td class="header-pad" style="background: linear-gradient(135deg, {color1} 0%, {color2} 100%); padding: 40px 30px; text-align: center;">
                            <h1 class="header-title" style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">{titulo}</h1>
                            <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.9); font-size: 15px;">{subtitulo}</p>
                        </td>
                    </tr>'''


def _footer(nombre_negocio="Reserfy"):
    """Genera el footer."""
    return f'''
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 25px 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0 0 8px 0; color: #1A1A1A; font-size: 14px; font-weight: 600;">{nombre_negocio}</p>
                            <p style="margin: 0; color: #9CA3AF; font-size: 12px;">Este email fue enviado automaticamente por Reserfy</p>
                        </td>
                    </tr>'''


def _info_row(icono, label, valor):
    """Genera una fila de información."""
    return f'''
                                            <tr>
                                                <td width="40%" style="padding: 8px 0; color: #6B7280; font-size: 13px; vertical-align: top;">{icono} {label}</td>
                                                <td width="60%" style="padding: 8px 0; color: #1A1A1A; font-size: 14px; font-weight: 500; vertical-align: top;">{valor}</td>
                                            </tr>'''


def _button(texto, link, color1="#912A5C", color2="#FA8F3E"):
    """Genera un boton CTA."""
    return f'''
                    <tr>
                        <td align="center" style="padding: 25px 30px;">
                            <table role="presentation" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="background: linear-gradient(135deg, {color1} 0%, {color2} 100%); border-radius: 8px;">
                                        <a href="{link}" style="display: inline-block; padding: 14px 28px; color: #ffffff; font-size: 15px; font-weight: 700; text-decoration: none;">{texto}</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''


# ============================================================================
# FUNCIONES GENERADORAS DE EMAIL
# ============================================================================

def generar_email_confirmacion(email_cliente, nombre_cliente, servicio, fecha_hora_utc,
                                nombre_negocio, token, timezone="America/Santo_Domingo"):
    """Genera el HTML para email de confirmacion de reserva."""
    tz = pytz.timezone(timezone)

    if fecha_hora_utc.tzinfo is None:
        fecha_hora_display = pytz.utc.localize(fecha_hora_utc).astimezone(tz)
    else:
        fecha_hora_display = fecha_hora_utc.astimezone(tz)

    fecha_str = fecha_hora_display.strftime('%d/%m/%Y')
    hora_str = fecha_hora_display.strftime('%I:%M %p')
    link_gestion = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/reserva/{token}/gestionar"

    info_rows = (
        _info_row("Empresa", f"<strong>{nombre_negocio}</strong>", "") +
        _info_row("Servicio", f"<strong>{servicio}</strong>", "") +
        _info_row("Fecha", f"<strong>{fecha_str}</strong>", "") +
        _info_row("Hora", f"<strong>{hora_str}</strong>", "")
    )

    contenido = f'''
                    {_header("Reserva Confirmada", "Tu cita ha sido agendada con exito")}
                    <tr>
                        <td class="body-pad" style="padding: 35px 30px; background-color: #ffffff;">
                            <h2 style="margin: 0 0 15px 0; color: #1A1A1A; font-size: 20px; font-weight: 600;">Hola {nombre_cliente},</h2>
                            <p style="margin: 0 0 20px 0; color: #4A4A4A; font-size: 15px; line-height: 1.6;">Gracias por reservar con nosotros. Tu cita ha sido confirmada exitosamente.</p>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #912A5C;">
                                <tr>
                                    <td style="padding: 15px;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                                            {info_rows}
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin: 20px 0; color: #4A4A4A; font-size: 14px;">Te esperamos puntualmente. Si necesitas cancelar o reprogramar, usa el boton de abajo.</p>
                        </td>
                    </tr>
                    {_button("Gestionar mi Reserva", link_gestion)}
                    <tr>
                        <td style="padding: 0 30px 25px; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #6B7280;">
                                O copia este enlace:<br>
                                <a href="{link_gestion}" style="color: #912A5C; font-size: 11px; word-break: break-all;">{link_gestion}</a>
                            </p>
                        </td>
                    </tr>
                    {_footer(nombre_negocio)}'''

    return _get_base_template().replace("{{contenido}}", contenido).replace("{{asunto}}", f"Reserva Confirmada - {nombre_negocio}")


def generar_email_cancelacion(cliente, negocio, reserva, timezone="America/Santo_Domingo"):
    """Genera el HTML para email de cancelacion de reserva."""
    tz = pytz.timezone(timezone)

    if reserva.fecha_hora.tzinfo is None:
        fecha_hora_display = pytz.utc.localize(reserva.fecha_hora).astimezone(tz)
    else:
        fecha_hora_display = reserva.fecha_hora.astimezone(tz)

    fecha_str = fecha_hora_display.strftime('%d/%m/%Y')
    hora_str = fecha_hora_display.strftime('%I:%M %p')
    link_reserva = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/b/{negocio.slug}"

    info_rows = (
        _info_row("Empresa", f"<strong>{negocio.nombre}</strong>", "") +
        _info_row("Servicio", f"<strong>{reserva.servicio}</strong>", "") +
        _info_row("Fecha", f"<strong>{fecha_str}</strong>", "") +
        _info_row("Hora", f"<strong>{hora_str}</strong>", "")
    )

    contenido = f'''
                    {_header("Reserva Cancelada", "Tu reserva ha sido cancelada", "#DC2626", "#991B1B")}
                    <tr>
                        <td class="body-pad" style="padding: 35px 30px; background-color: #ffffff;">
                            <h2 style="margin: 0 0 15px 0; color: #1A1A1A; font-size: 20px; font-weight: 600;">Hola {cliente.nombre},</h2>
                            <p style="margin: 0 0 20px 0; color: #4A4A4A; font-size: 15px; line-height: 1.6;">Tu reserva ha sido cancelada exitosamente.</p>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #fef2f2; border-radius: 8px; border-left: 4px solid #DC2626;">
                                <tr>
                                    <td style="padding: 15px;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                                            {info_rows}
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #fef3c7; border-radius: 8px; margin-top: 20px;">
                                <tr>
                                    <td style="padding: 15px;">
                                        <p style="margin: 0; font-size: 13px; color: #92400e;">
                                            <strong>Informacion:</strong> Si cancelaste por error, puedes crear una nueva reserva en cualquier momento.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    {_button("Agendar Nueva Cita", link_reserva, "#059669", "#047857")}
                    {_footer(negocio.nombre)}'''

    return _get_base_template().replace("{{contenido}}", contenido).replace("{{asunto}}", f"Reserva Cancelada - {negocio.nombre}")


def generar_email_recordatorio(cliente, negocio, reserva, timezone="America/Santo_Domingo"):
    """Genera el HTML para email de recordatorio (24h antes)."""
    tz = pytz.timezone(timezone)

    if reserva.fecha_hora.tzinfo is None:
        fecha_hora_display = pytz.utc.localize(reserva.fecha_hora).astimezone(tz)
    else:
        fecha_hora_display = reserva.fecha_hora.astimezone(tz)

    fecha_str = fecha_hora_display.strftime('%d/%m/%Y')
    hora_str = fecha_hora_display.strftime('%I:%M %p')
    link_gestion = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/reserva/{reserva.token}/gestionar"

    info_rows = (
        _info_row("Empresa", f"<strong>{negocio.nombre}</strong>", "") +
        _info_row("Servicio", f"<strong>{reserva.servicio}</strong>", "") +
        _info_row("Fecha", f"<strong>{fecha_str}</strong>", "") +
        _info_row("Hora", f"<strong>{hora_str}</strong>", "")
    )

    contenido = f'''
                    {_header("Recordatorio de Cita", "Tu cita es manana", "#059669", "#047857")}
                    <tr>
                        <td class="body-pad" style="padding: 35px 30px; background-color: #ffffff;">
                            <h2 style="margin: 0 0 15px 0; color: #1A1A1A; font-size: 20px; font-weight: 600;">Hola {cliente.nombre},</h2>
                            <p style="margin: 0 0 20px 0; color: #4A4A4A; font-size: 15px; line-height: 1.6;">Este es un recordatorio amigable de tu proxima cita programada.</p>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #ecfdf5; border: 2px solid #059669; border-radius: 12px; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                                            {info_rows}
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8f9fa; border-radius: 8px; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 15px;">
                                        <p style="margin: 0 0 8px 0; font-size: 14px; color: #1A1A1A; font-weight: 600;">Tips:</p>
                                        <p style="margin: 0; font-size: 13px; color: #4A4A4A; line-height: 1.6;">
                                            - Llega 5-10 minutos antes<br>
                                            - Cancela con 24h de anticipacion<br>
                                            - Trae cualquier referencia especial
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    {_button("Cancelar o Reprogramar", link_gestion, "#DC2626", "#991B1B")}
                    {_footer(negocio.nombre)}'''

    return _get_base_template().replace("{{contenido}}", contenido).replace("{{asunto}}", f"Recordatorio: Cita manana - {negocio.nombre}")


def generar_email_notificacion_negocio(negocio, cliente, reserva, timezone="America/Santo_Domingo"):
    """Genera el HTML para notificacion al negocio de nueva reserva."""
    tz = pytz.timezone(timezone)

    if reserva.fecha_hora.tzinfo is None:
        fecha_hora_display = pytz.utc.localize(reserva.fecha_hora).astimezone(tz)
    else:
        fecha_hora_display = reserva.fecha_hora.astimezone(tz)

    fecha_str = fecha_hora_display.strftime('%d/%m/%Y')
    hora_str = fecha_hora_display.strftime('%I:%M %p')
    link_dashboard = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/reservas"

    info_rows = (
        _info_row("Cliente", f"<strong>{cliente.nombre}</strong>", "") +
        _info_row("Email", cliente.email or "-", "") +
        _info_row("Telefono", cliente.telefono or "-", "") +
        _info_row("Servicio", f"<strong>{reserva.servicio}</strong>", "") +
        _info_row("Fecha", f"<strong>{fecha_str}</strong>", "") +
        _info_row("Hora", f"<strong>{hora_str}</strong>", "")
    )

    contenido = f'''
                    {_header("Nueva Reserva", f"Tienes una nueva reserva en {negocio.nombre}")}
                    <tr>
                        <td class="body-pad" style="padding: 35px 30px; background-color: #ffffff;">
                            <h2 style="margin: 0 0 20px 0; color: #1A1A1A; font-size: 18px; font-weight: 600;">Detalles del Cliente</h2>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #912A5C;">
                                <tr>
                                    <td style="padding: 15px;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                                            {info_rows}
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    {_button("Ver en Dashboard", link_dashboard)}
                    {_footer("Reserfy - Sistema de Reservas")}'''

    return _get_base_template().replace("{{contenido}}", contenido).replace("{{asunto}}", f"Nueva Reserva - {cliente.nombre}")


# ============================================================================
# FUNCIONES DE ENVÍO
# ============================================================================

def enviar_email(destinatario, asunto, contenido_html):
    """Envia un email usando SendGrid con manejo robusto de errores."""
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        mensaje = SGMail(
            from_email=MAIL_SENDER,
            to_emails=destinatario,
            subject=asunto,
            html_content=contenido_html
        )
        response = sg.send(mensaje)
        print(f"Email enviado a {destinatario}: {response.status_code}")
        return True
    except Exception as e:
        print(f"Error enviando email a {destinatario}: {e}")
        if hasattr(e, 'body'):
            print(f"   Body: {e.body}")
        if hasattr(e, 'status_code'):
            print(f"   Status: {e.status_code}")
        return False


def enviar_confirmacion(email_cliente, nombre_cliente, servicio, fecha_hora,
                       nombre_negocio, token, timezone="America/Santo_Domingo"):
    """Envia email de confirmacion al cliente."""
    html = generar_email_confirmacion(
        email_cliente=email_cliente,
        nombre_cliente=nombre_cliente,
        servicio=servicio,
        fecha_hora_utc=fecha_hora,
        nombre_negocio=nombre_negocio,
        token=token,
        timezone=timezone
    )
    return enviar_email(
        destinatario=email_cliente,
        asunto=f"Reserva Confirmada - {nombre_negocio}",
        contenido_html=html
    )


def enviar_notificacion_negocio(negocio, cliente, reserva):
    """Envia notificacion de nueva reserva al negocio."""
    try:
        html = generar_email_notificacion_negocio(negocio, cliente, reserva, negocio.timezone)
        return enviar_email(
            destinatario=negocio.email,
            asunto=f"Nueva Reserva - {cliente.nombre}",
            contenido_html=html
        )
    except Exception as e:
        print(f"Error generando notificacion al negocio: {e}")
        return False


def enviar_cancelacion_emails(cliente, negocio, reserva):
    """Envia emails de cancelacion al cliente y al negocio."""
    resultados = {'cliente': False, 'negocio': False}

    if not cliente or not cliente.email:
        return resultados

    # Email al cliente
    try:
        html = generar_email_cancelacion(cliente, negocio, reserva, negocio.timezone)
        resultados['cliente'] = enviar_email(
            destinatario=cliente.email,
            asunto=f"Reserva Cancelada - {negocio.nombre}",
            contenido_html=html
        )
    except Exception as e:
        print(f"Error enviando email al cliente: {e}")

    # Email al negocio
    try:
        html = generar_email_notificacion_negocio(negocio, cliente, reserva, negocio.timezone)
        resultados['negocio'] = enviar_email(
            destinatario=negocio.email,
            asunto=f"Reserva Cancelada - {cliente.nombre}",
            contenido_html=html
        )
    except Exception as e:
        print(f"Error enviando email al negocio: {e}")

    return resultados


def enviar_recordatorio(cliente, negocio, reserva):
    """Envia email de recordatorio 24 horas antes de la cita."""
    if not cliente or not cliente.email:
        return False

    try:
        html = generar_email_recordatorio(cliente, negocio, reserva, negocio.timezone)
        return enviar_email(
            destinatario=cliente.email,
            asunto=f"Recordatorio: Cita manana - {negocio.nombre}",
            contenido_html=html
        )
    except Exception as e:
        print(f"Error enviando recordatorio: {e}")
        return False