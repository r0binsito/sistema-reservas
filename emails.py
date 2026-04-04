"""
Plantillas de Email para Reserfy
Diseño UI/UX moderno estilo SaaS con estructura HTML completa para evitar filtros de spam
"""

# ============================================================================
# PLANTILLA BASE - Estructura común para todos los emails
# ============================================================================

BASE_EMAIL_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{{asunto}}</title>
    <style type="text/css">
        /* Reset de estilos para clientes de email */
        body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
        img {{ -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }}
        table {{ border-collapse: collapse !important; }}
        body {{ height: 100% !important; margin: 0 !important; padding: 0 !important; width: 100% !important; }}

        /* Estilos base */
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f4f5;
            margin: 0;
            padding: 0;
        }}

        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}

        .header {{
            background: linear-gradient(135deg, #912A5C 0%, #FA8F3E 100%);
            padding: 40px 30px;
            text-align: center;
        }}

        .header h1 {{
            color: #ffffff;
            margin: 0;
            font-size: 28px;
            font-weight: 700;
        }}

        .header p {{
            color: rgba(255, 255, 255, 0.9);
            margin: 10px 0 0 0;
            font-size: 16px;
        }}

        .body {{
            padding: 40px 30px;
            background-color: #ffffff;
        }}

        .body h2 {{
            color: #1A1A1A;
            font-size: 22px;
            margin: 0 0 20px 0;
            font-weight: 600;
        }}

        .body p {{
            color: #4A4A4A;
            font-size: 16px;
            line-height: 1.6;
            margin: 0 0 16px 0;
        }}

        .info-box {{
            background-color: #f8f9fa;
            border-left: 4px solid #912A5C;
            padding: 20px;
            margin: 25px 0;
            border-radius: 8px;
        }}

        .info-row {{
            display: table;
            width: 100%;
            margin-bottom: 15px;
        }}

        .info-row:last-child {{
            margin-bottom: 0;
        }}

        .info-label {{
            display: table-cell;
            color: #6B7280;
            font-size: 14px;
            padding-right: 15px;
            vertical-align: top;
            width: 140px;
        }}

        .info-value {{
            display: table-cell;
            color: #1A1A1A;
            font-size: 15px;
            font-weight: 500;
            vertical-align: top;
        }}

        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #912A5C 0%, #FA8F3E 100%);
            color: #ffffff !important;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 700;
            font-size: 16px;
            margin: 25px 0;
            text-align: center;
        }}

        .cta-button:hover {{
            background: linear-gradient(135deg, #FA8F3E 0%, #912A5C 100%);
        }}

        .footer {{
            background-color: #f8f9fa;
            padding: 30px;
            text-align: center;
            border-top: 1px solid #e5e7eb;
        }}

        .footer p {{
            color: #9CA3AF;
            font-size: 13px;
            margin: 0 0 10px 0;
            line-height: 1.5;
        }}

        .footer a {{
            color: #912A5C;
            text-decoration: none;
        }}

        .footer a:hover {{
            text-decoration: underline;
        }}

        .status-badge {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .status-confirmed {{
            background-color: #d1fae5;
            color: #065f46;
        }}

        .status-cancelled {{
            background-color: #fee2e2;
            color: #991b1b;
        }}

        .status-reminder {{
            background-color: #fef3c7;
            color: #92400e;
        }}

        /* Responsive */
        @media screen and (max-width: 600px) {{
            .email-container {{
                border-radius: 0 !important;
            }}
            .header {{
                padding: 30px 20px !important;
            }}
            .body {{
                padding: 30px 20px !important;
            }}
            .info-row {{
                display: block;
            }}
            .info-label, .info-value {{
                display: block;
                width: 100% !important;
            }}
            .info-label {{
                margin-bottom: 5px;
            }}
        }}
    </style>
</head>
<body>
    <div style="background-color:#f4f4f5;padding:20px;">
        <table role="presentation" style="width:100%;border-collapse:collapse;">
            <tr>
                <td align="center">
                    <!-- Contenido del email -->
                    {{contenido}}
                </td>
            </tr>
        </table>
    </div>
</body>
</html>"""

# ============================================================================
# EMAIL DE CONFIRMACIÓN DE RESERVA
# ============================================================================

CONFIRMACION_TEMPLATE = """
                    <div class="email-container">
                        <div class="header">
                            <h1>¡Reserva Confirmada!</h1>
                            <p>Tu cita ha sido agendada con éxito</p>
                        </div>
                        <div class="body">
                            <h2>Hola {nombre_cliente},</h2>
                            <p>Gracias por reservar con nosotros. Tu cita ha sido confirmada exitosamente.</p>

                            <div class="info-box">
                                <div class="info-row">
                                    <span class="info-label">🏢 Negocio:</span>
                                    <span class="info-value"><strong>{nombre_negocio}</strong></span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">✂️ Servicio:</span>
                                    <span class="info-value"><strong>{servicio}</strong></span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">📅 Fecha:</span>
                                    <span class="info-value"><strong>{fecha}</strong></span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">🕐 Hora:</span>
                                    <span class="info-value"><strong>{hora}</strong></span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">📍 Timezone:</span>
                                    <span class="info-value">{timezone}</span>
                                </div>
                            </div>

                            <p>Te esperamos puntualmente. Si necesitas cancelar o reprogramar, puedes hacerlo usando el botón de abajo.</p>

                            <center>
                                <a href="{link_gestion}" class="cta-button">Gestionar mi Reserva</a>
                            </center>

                            <p style="margin-top:25px;font-size:14px;color:#6B7280;">
                                O copia este enlace en tu navegador:<br>
                                <a href="{link_gestion}" style="color:#912A5C;">{link_gestion}</a>
                            </p>
                        </div>
                        <div class="footer">
                            <p><strong>{nombre_negocio}</strong></p>
                            <p>Este email fue enviado automáticamente por Reserfy</p>
                            <p style="font-size:12px;color:#9CA3AF;">
                                ¿Tienes preguntas? Contáctanos directamente respondiendo este correo.
                            </p>
                        </div>
                    </div>
"""

# ============================================================================
# EMAIL DE CANCELACIÓN DE RESERVA
# ============================================================================

CANCELACION_TEMPLATE = """
                    <div class="email-container">
                        <div class="header" style="background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%);">
                            <h1>Reserva Cancelada</h1>
                            <p>Tu reserva ha sido cancelada</p>
                        </div>
                        <div class="body">
                            <h2>Hola {nombre_cliente},</h2>
                            <p>Tu reserva ha sido cancelada exitosamente. A continuación encontrarás los detalles:</p>

                            <div class="info-box" style="border-left-color: #DC2626;">
                                <div class="info-row">
                                    <span class="info-label">🏢 Negocio:</span>
                                    <span class="info-value"><strong>{nombre_negocio}</strong></span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">✂️ Servicio:</span>
                                    <span class="info-value"><strong>{servicio}</strong></span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">📅 Fecha programada:</span>
                                    <span class="info-value"><strong>{fecha}</strong></span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">🕐 Hora programada:</span>
                                    <span class="info-value"><strong>{hora}</strong></span>
                                </div>
                            </div>

                            <p style="background-color:#fef3c7;padding:15px;border-radius:8px;margin:20px 0;">
                                <strong>ℹ️ Información:</strong> Si cancelaste por error o deseas reagendar, puedes crear una nueva reserva en cualquier momento.
                            </p>

                            <center>
                                <a href="{link_reserva}" class="cta-button" style="background: linear-gradient(135deg, #059669 0%, #047857 100%);">
                                    Agendar Nueva Cita
                                </a>
                            </center>
                        </div>
                        <div class="footer">
                            <p><strong>{nombre_negocio}</strong></p>
                            <p>Esperamos verte pronto</p>
                            <p style="font-size:12px;color:#9CA3AF;">
                                Este email fue enviado automáticamente por Reserfy
                            </p>
                        </div>
                    </div>
"""

# ============================================================================
# EMAIL DE RECORDATORIO (24 horas antes)
# ============================================================================

RECORDATORIO_TEMPLATE = """
                    <div class="email-container">
                        <div class="header" style="background: linear-gradient(135deg, #059669 0%, #047857 100%);">
                            <h1>Recordatorio de Cita</h1>
                            <p>Tu cita es mañana</p>
                        </div>
                        <div class="body">
                            <h2>Hola {nombre_cliente},</h2>
                            <p>Este es un recordatorio amigable de tu próxima cita programada.</p>

                            <div style="background-color:#ecfdf5;border:2px solid #059669;border-radius:12px;padding:25px;margin:25px 0;">
                                <div style="text-align:center;margin-bottom:20px;">
                                    <span class="status-badge status-reminder">🔔 Recordatorio</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">🏢 Negocio:</span>
                                    <span class="info-value"><strong>{nombre_negocio}</strong></span>
                                </div>
                                <hr style="border:none;border-top:1px solid #d1fae5;margin:15px 0;">
                                <div class="info-row">
                                    <span class="info-label">✂️ Servicio:</span>
                                    <span class="info-value"><strong>{servicio}</strong></span>
                                </div>
                                <hr style="border:none;border-top:1px solid #d1fae5;margin:15px 0;">
                                <div class="info-row">
                                    <span class="info-label">📅 Fecha:</span>
                                    <span class="info-value"><strong>{fecha}</strong></span>
                                </div>
                                <hr style="border:none;border-top:1px solid #d1fae5;margin:15px 0;">
                                <div class="info-row">
                                    <span class="info-label">🕐 Hora:</span>
                                    <span class="info-value"><strong>{hora}</strong></span>
                                </div>
                            </div>

                            <p style="background-color:#f8f9fa;padding:15px;border-radius:8px;margin:20px 0;">
                                <strong>💡 Tips:</strong><br>
                                • Llega 5-10 minutos antes de tu hora programada<br>
                                • Si necesitas cancelar, hazlo con al menos 24 horas de anticipación<br>
                                • Trae cualquier referencia o instrucción especial si aplica
                            </p>

                            <center>
                                <a href="{link_gestion}" class="cta-button" style="background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%);">
                                    Cancelar o Reprogramar
                                </a>
                            </center>
                        </div>
                        <div class="footer">
                            <p><strong>{nombre_negocio}</strong></p>
                            <p>¡Nos vemos pronto!</p>
                            <p style="font-size:12px;color:#9CA3AF;">
                                Este email fue enviado automáticamente por Reserfy
                            </p>
                        </div>
                    </div>
"""

# ============================================================================
# EMAIL DE NOTIFICACIÓN AL NEGOCIO (Nueva Reserva)
# ============================================================================

NOTIFICACION_NEGOCIO_TEMPLATE = """
                    <div class="email-container">
                        <div class="header">
                            <h1>📅 Nueva Reserva</h1>
                            <p>Tienes una nueva reserva en {nombre_negocio}</p>
                        </div>
                        <div class="body">
                            <h2>Detalles del Cliente</h2>

                            <div class="info-box">
                                <div class="info-row">
                                    <span class="info-label">👤 Nombre:</span>
                                    <span class="info-value"><strong>{nombre_cliente}</strong></span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">📧 Email:</span>
                                    <span class="info-value">{email_cliente}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">📞 Teléfono:</span>
                                    <span class="info-value">{telefono_cliente}</span>
                                </div>
                                <hr style="border:none;border-top:1px solid #e5e7eb;margin:15px 0;">
                                <div class="info-row">
                                    <span class="info-label">✂️ Servicio:</span>
                                    <span class="info-value"><strong>{servicio}</strong></span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">📅 Fecha:</span>
                                    <span class="info-value"><strong>{fecha}</strong></span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">🕐 Hora:</span>
                                    <span class="info-value"><strong>{hora}</strong></span>
                                </div>
                            </div>

                            <center>
                                <a href="{link_dashboard}" class="cta-button">Ver en Dashboard →</a>
                            </center>
                        </div>
                        <div class="footer">
                            <p>Reserfy - Sistema de Reservas</p>
                            <p style="font-size:12px;color:#9CA3AF;">
                                Notificación automática generada por Reserfy
                            </p>
                        </div>
                    </div>
"""


# ============================================================================
# FUNCIONES DE ENVÍO DE EMAILS
# ============================================================================

import os
import pytz
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SGMail

MAIL_SENDER = os.getenv("MAIL_DEFAULT_SENDER")


def obtener_email_base():
    """Retorna la plantilla base de email."""
    return BASE_EMAIL_TEMPLATE


def generar_email_confirmacion(email_cliente, nombre_cliente, servicio, fecha_hora_utc,
                                nombre_negocio, token, timezone="America/Santo_Domingo"):
    """
    Genera el HTML para email de confirmación de reserva.

    Args:
        email_cliente: Email del cliente
        nombre_cliente: Nombre del cliente
        servicio: Nombre del servicio reservado
        fecha_hora_utc: Fecha y hora en UTC (datetime object)
        nombre_negocio: Nombre del negocio
        token: Token único de la reserva para gestión
        timezone: Timezone para mostrar la hora local

    Returns:
        str: HTML completo del email
    """
    tz = pytz.timezone(timezone)

    # Convertir de UTC a timezone local
    if fecha_hora_utc.tzinfo is None:
        fecha_hora_display = pytz.utc.localize(fecha_hora_utc).astimezone(tz)
    else:
        fecha_hora_display = fecha_hora_utc.astimezone(tz)

    fecha_str = fecha_hora_display.strftime('%d/%m/%Y')
    hora_str = fecha_hora_display.strftime('%I:%M %p')
    link_gestion = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/reserva/{token}/gestionar"

    contenido = CONFIRMACION_TEMPLATE.format(
        nombre_cliente=nombre_cliente,
        nombre_negocio=nombre_negocio,
        servicio=servicio,
        fecha=fecha_str,
        hora=hora_str,
        timezone=timezone,
        link_gestion=link_gestion
    )

    return BASE_EMAIL_TEMPLATE.replace("{{contenido}}", contenido).replace("{{asunto}}", f"Reserva Confirmada - {nombre_negocio}")


def generar_email_cancelacion(cliente, negocio, reserva, timezone="America/Santo_Domingo"):
    """
    Genera el HTML para email de cancelación de reserva.

    Args:
        cliente: Objeto Cliente con nombre y email
        negocio: Objeto Negocio
        reserva: Objeto Reserva con servicio y fecha_hora
        timezone: Timezone para mostrar la hora local

    Returns:
        str: HTML completo del email
    """
    tz = pytz.timezone(timezone)

    # Convertir fecha a timezone local
    if reserva.fecha_hora.tzinfo is None:
        fecha_hora_display = pytz.utc.localize(reserva.fecha_hora).astimezone(tz)
    else:
        fecha_hora_display = reserva.fecha_hora.astimezone(tz)

    fecha_str = fecha_hora_display.strftime('%d/%m/%Y')
    hora_str = fecha_hora_display.strftime('%I:%M %p')
    link_reserva = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/b/{negocio.slug}"

    contenido = CANCELACION_TEMPLATE.format(
        nombre_cliente=cliente.nombre,
        nombre_negocio=negocio.nombre,
        servicio=reserva.servicio,
        fecha=fecha_str,
        hora=hora_str,
        link_reserva=link_reserva
    )

    return BASE_EMAIL_TEMPLATE.replace("{{contenido}}", contenido).replace("{{asunto}}", f"Reserva Cancelada - {negocio.nombre}")


def generar_email_recordatorio(cliente, negocio, reserva, timezone="America/Santo_Domingo"):
    """
    Genera el HTML para email de recordatorio (24h antes).

    Args:
        cliente: Objeto Cliente con nombre y email
        negocio: Objeto Negocio
        reserva: Objeto Reserva con servicio y fecha_hora
        timezone: Timezone para mostrar la hora local

    Returns:
        str: HTML completo del email
    """
    tz = pytz.timezone(timezone)

    # Convertir fecha a timezone local
    if reserva.fecha_hora.tzinfo is None:
        fecha_hora_display = pytz.utc.localize(reserva.fecha_hora).astimezone(tz)
    else:
        fecha_hora_display = reserva.fecha_hora.astimezone(tz)

    fecha_str = fecha_hora_display.strftime('%d/%m/%Y')
    hora_str = fecha_hora_display.strftime('%I:%M %p')
    link_gestion = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/reserva/{reserva.token}/gestionar"

    contenido = RECORDATORIO_TEMPLATE.format(
        nombre_cliente=cliente.nombre,
        nombre_negocio=negocio.nombre,
        servicio=reserva.servicio,
        fecha=fecha_str,
        hora=hora_str,
        link_gestion=link_gestion
    )

    return BASE_EMAIL_TEMPLATE.replace("{{contenido}}", contenido).replace("{{asunto}}", f"Recordatorio: Cita mañana - {negocio.nombre}")


def generar_email_notificacion_negocio(negocio, cliente, reserva, timezone="America/Santo_Domingo"):
    """
    Genera el HTML para notificación al negocio de nueva reserva.

    Args:
        negocio: Objeto Negocio
        cliente: Objeto Cliente
        reserva: Objeto Reserva
        timezone: Timezone para mostrar la hora local

    Returns:
        str: HTML completo del email
    """
    tz = pytz.timezone(timezone)

    # Convertir fecha a timezone local
    if reserva.fecha_hora.tzinfo is None:
        fecha_hora_display = pytz.utc.localize(reserva.fecha_hora).astimezone(tz)
    else:
        fecha_hora_display = reserva.fecha_hora.astimezone(tz)

    fecha_str = fecha_hora_display.strftime('%d/%m/%Y')
    hora_str = fecha_hora_display.strftime('%I:%M %p')
    link_dashboard = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/reservas"

    contenido = NOTIFICACION_NEGOCIO_TEMPLATE.format(
        nombre_negocio=negocio.nombre,
        nombre_cliente=cliente.nombre,
        email_cliente=cliente.email or '—',
        telefono_cliente=cliente.telefono or '—',
        servicio=reserva.servicio,
        fecha=fecha_str,
        hora=hora_str,
        link_dashboard=link_dashboard
    )

    return BASE_EMAIL_TEMPLATE.replace("{{contenido}}", contenido).replace("{{asunto}}", f"📅 Nueva Reserva - {cliente.nombre}")


def enviar_email(destinatario, asunto, contenido_html):
    """
    Envía un email usando SendGrid con manejo robusto de errores.

    Args:
        destinatario: Email del destinatario
        asunto: Asunto del email
        contenido_html: Contenido HTML del email

    Returns:
        bool: True si se envió exitosamente, False en caso de error
    """
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        mensaje = SGMail(
            from_email=MAIL_SENDER,
            to_emails=destinatario,
            subject=asunto,
            html_content=contenido_html
        )
        response = sg.send(mensaje)
        print(f"✅ Email enviado a {destinatario}: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Error enviando email a {destinatario}: {e}")
        if hasattr(e, 'body'):
            print(f"   Body: {e.body}")
        if hasattr(e, 'status_code'):
            print(f"   Status: {e.status_code}")
        return False


def enviar_confirmacion(email_cliente, nombre_cliente, servicio, fecha_hora,
                       nombre_negocio, token, timezone="America/Santo_Domingo"):
    """Envía email de confirmación al cliente."""
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
        asunto=f"Reserva Confirmada — {nombre_negocio}",
        contenido_html=html
    )


def enviar_notificacion_negocio(negocio, cliente, reserva):
    """Envía notificación de nueva reserva al negocio."""
    try:
        html = generar_email_notificacion_negocio(negocio, cliente, reserva, negocio.timezone)
        return enviar_email(
            destinatario=negocio.email,
            asunto=f"📅 Nueva Reserva — {cliente.nombre}",
            contenido_html=html
        )
    except Exception as e:
        print(f"Error generando notificación al negocio: {e}")
        return False


def enviar_cancelacion_emails(cliente, negocio, reserva):
    """Envía emails de cancelación al cliente y al negocio."""
    resultados = {'cliente': False, 'negocio': False}

    if not cliente or not cliente.email:
        return resultados

    # Email al cliente
    try:
        html = generar_email_cancelacion(cliente, negocio, reserva, negocio.timezone)
        resultados['cliente'] = enviar_email(
            destinatario=cliente.email,
            asunto=f"Reserva Cancelada — {negocio.nombre}",
            contenido_html=html
        )
    except Exception as e:
        print(f"Error enviando email al cliente: {e}")

    # Email al negocio
    try:
        html = generar_email_notificacion_negocio(negocio, cliente, reserva, negocio.timezone)
        resultados['negocio'] = enviar_email(
            destinatario=negocio.email,
            asunto=f"Reserva Cancelada — {cliente.nombre}",
            contenido_html=html
        )
    except Exception as e:
        print(f"Error enviando email al negocio: {e}")

    return resultados


def enviar_recordatorio(cliente, negocio, reserva):
    """Envía email de recordatorio 24 horas antes de la cita."""
    if not cliente or not cliente.email:
        return False

    try:
        html = generar_email_recordatorio(cliente, negocio, reserva, negocio.timezone)
        return enviar_email(
            destinatario=cliente.email,
            asunto=f"Recordatorio: Cita mañana — {negocio.nombre}",
            contenido_html=html
        )
    except Exception as e:
        print(f"Error enviando recordatorio: {e}")
        return False