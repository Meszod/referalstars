from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Channel


class ChannelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self) -> list[Channel]:
        stmt = select(Channel).where(Channel.is_active.is_(True)).order_by(Channel.id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, channel_pk: int) -> Channel | None:
        return await self.session.get(Channel, channel_pk)

    async def get_by_channel_id(self, channel_id: int) -> Channel | None:
        stmt = select(Channel).where(Channel.channel_id == channel_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def add(self, *, channel_id: int, username: str | None, title: str, invite_link: str | None) -> Channel:
        ch = Channel(channel_id=channel_id, username=username, title=title, invite_link=invite_link)
        self.session.add(ch)
        await self.session.flush()
        return ch

    async def remove(self, channel_pk: int) -> bool:
        res = await self.session.execute(delete(Channel).where(Channel.id == channel_pk))
        return (res.rowcount or 0) > 0
