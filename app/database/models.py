"""SQLAlchemy 2.x modellari. Muhim qoidalar DB darajasida ham (UNIQUE/CHECK) himoyalangan."""
from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class WithdrawalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TransactionType(str, enum.Enum):
    REFERRAL = "referral"
    BONUS = "bonus"
    WITHDRAWAL = "withdrawal"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="balance_non_negative"),
        CheckConstraint("referred_by IS NULL OR referred_by <> id", name="no_self_referral"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    balance: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    total_earned: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    total_withdrawn: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    referral_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), index=True)
    referred_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint("referred_user_id", name="uq_referrals_referred_user_id"),
        CheckConstraint("referrer_id <> referred_user_id", name="not_self"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referrer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    referred_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    reward: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    # Reward faqat referred user majburiy kanallarga obuna bo'lgach beriladi.
    # rewarded_at NULL bo'lsa referral hali "pending".
    rewarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Withdrawal(Base):
    __tablename__ = "withdrawals"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("status IN ('pending','approved','rejected')", name="status_valid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(16), default=WithdrawalStatus.PENDING.value, server_default="pending", index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(256))
    invite_link: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('referral','bonus','withdrawal','refund','admin_adjustment')", name="type_valid"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # manfiy bo'lishi mumkin
    type: Mapped[str] = mapped_column(String(32), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserMilestone(Base):
    __tablename__ = "user_milestones"
    __table_args__ = (UniqueConstraint("user_id", "milestone", name="uq_user_milestones_user_milestone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    milestone: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyBonusClaim(Base):
    __tablename__ = "daily_bonus_claims"
    __table_args__ = (UniqueConstraint("user_id", "claim_date", name="uq_daily_bonus_claims_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    claim_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[int] = mapped_column(Integer)
    streak: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Setting(Base):
    """Admin tomonidan o'zgartiriladigan sozlamalar (key-value)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
