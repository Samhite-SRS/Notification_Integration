"""
All direct database access lives here (spec's "Repository/Database Layer").
The service layer never touches SQLAlchemy directly - it calls these
functions, so persistence can change without touching business logic.
"""
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationDelivery


def create_notification(db: Session, *, title: str, message: str) -> Notification:
    notification = Notification(title=title, message=message)
    db.add(notification)
    db.flush()  # assign the id without committing yet
    return notification


def add_delivery(
    db: Session,
    *,
    notification_id: str,
    channel: str,
    destination: str,
    provider: str,
    status: str = "PENDING",
) -> NotificationDelivery:
    delivery = NotificationDelivery(
        notification_id=notification_id,
        channel=channel,
        destination=destination,
        provider=provider,
        status=status,
    )
    db.add(delivery)
    db.flush()
    return delivery


def get_notification(db: Session, notification_id: str) -> Notification | None:
    return db.get(Notification, notification_id)


def get_delivery(db: Session, delivery_id: str) -> NotificationDelivery | None:
    return db.get(NotificationDelivery, delivery_id)


def find_delivery_by_provider_message_id(db: Session, provider_message_id: str) -> NotificationDelivery | None:
    stmt = select(NotificationDelivery).where(NotificationDelivery.provider_message_id == provider_message_id)
    return db.execute(stmt).scalar_one_or_none()


def list_notifications(
    db: Session,
    *,
    channel: str | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Notification], int]:
    stmt = select(Notification)

    if channel or status or search:
        stmt = stmt.join(NotificationDelivery)
        if channel:
            stmt = stmt.where(NotificationDelivery.channel == channel.upper())
        if status:
            stmt = stmt.where(NotificationDelivery.status == status.upper())
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Notification.title.ilike(like),
                    Notification.message.ilike(like),
                    NotificationDelivery.destination.ilike(like),
                    Notification.id.ilike(like),
                )
            )
        stmt = stmt.distinct()

    total = len(db.execute(stmt).unique().scalars().all())

    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    items = list(db.execute(stmt).unique().scalars().all())
    return items, total


def update_delivery_status(
    db: Session,
    delivery: NotificationDelivery,
    *,
    status: str,
    provider_message_id: str | None = None,
    error_message: str | None = None,
    increment_retry: bool = False,
) -> NotificationDelivery:
    delivery.status = status
    if provider_message_id is not None:
        delivery.provider_message_id = provider_message_id
    # error_message is only ever cleared on a successful transition, never
    # silently dropped, so history keeps the most recent error around.
    if status in ("SENT", "DELIVERED"):
        delivery.error_message = None
    elif error_message is not None:
        delivery.error_message = error_message
    if increment_retry:
        delivery.retry_count += 1
    db.flush()
    return delivery


def stats(db: Session) -> dict:
    all_deliveries = db.execute(select(NotificationDelivery)).scalars().all()
    total_notifications = db.execute(select(Notification)).scalars().all()
    return {
        "total": len(total_notifications),
        "pending": sum(1 for d in all_deliveries if d.status == "PENDING"),
        "delivered": sum(1 for d in all_deliveries if d.status in ("SENT", "DELIVERED")),
        "failed": sum(1 for d in all_deliveries if d.status == "FAILED"),
    }
