# Revyo 🗓️
Sistema SaaS de reservas para barberías, gimnasios, spas y más.

## Estructura
```
revyo/
├── app.py                  # Entrada de la app
├── config.py               # Configuración por entorno
├── requirements.txt
├── .env.example
├── models/
│   └── models.py           # Owner, Business, Service, Appointment...
├── routes/
│   ├── main.py             # Landing page
│   ├── auth.py             # Registro / Login
│   ├── dashboard.py        # Panel del dueño
│   ├── booking.py          # Página pública de reservas
│   └── payment.py          # MercadoPago
├── templates/
│   ├── landing.html        # Página de ventas
│   ├── auth/               # Login, Register
│   ├── dashboard/          # Panel, Servicios, Horarios, Personalizar
│   ├── booking/            # Página pública + Confirmación
│   └── payment/            # Planes
└── static/
    ├── css/
    │   ├── styles.css      # Landing + Auth + Dashboard
    │   └── booking.css     # Página pública (con CSS vars dinámicos)
    └── js/main.js

```

## Rutas principales
| Ruta | Descripción |
|------|-------------|
| `/` | Landing page (ventas) |
| `/register` | Registro de dueño |
| `/login` | Login |
| `/dashboard` | Panel del dueño |
| `/dashboard/customize` | Personalizar página |
| `/dashboard/services` | Gestionar servicios |
| `/dashboard/hours` | Horarios de atención |
| `/dashboard/appointments` | Ver reservas |
| `/planes` | Planes y suscripción |
| `/b/<slug>` | Página pública del negocio |
| `/webhook/mercadopago` | IPN de MercadoPago |

## Modelos de datos
- **Owner** — dueño del negocio (cliente del SaaS)
- **Subscription** — suscripción mensual (MercadoPago)
- **Business** — negocio con personalización visual
- **Service** — servicios que ofrece el negocio
- **WorkingHours** — horarios de atención por día
- **Appointment** — reservas de los clientes

## Personalización por negocio
Cada negocio puede configurar:
- Nombre, descripción, categoría
- Logo (upload)
- Colores: primario, secundario, acento, texto
- Fuente tipográfica (9 Google Fonts)
- Horarios de atención
- Servicios con precio y duración
- Tiempo mínimo de anticipación
- Máximo de días por adelantado
