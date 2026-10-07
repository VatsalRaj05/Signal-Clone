import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.user import User
from app.models.contact import Contact
from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember, MemberRole
from app.models.message import Message, MessageType
from app.models.message_receipt import MessageReceipt, ReceiptStatus

# Deterministic test users
USERS_DATA = [
    {"username": "alice", "phone": "+111111111", "display_name": "Alice"},
    {"username": "bob", "phone": "+222222222", "display_name": "Bob"},
    {"username": "charlie", "phone": "+333333333", "display_name": "Charlie"},
    {"username": "david", "phone": "+444444444", "display_name": "David"},
    {"username": "emma", "phone": "+555555555", "display_name": "Emma"},
    {"username": "frank", "phone": "+666666666", "display_name": "Frank"},
]

async def seed_users(session):
    users = {}
    password_hash = hash_password("password123")
    
    for u_data in USERS_DATA:
        result = await session.execute(select(User).where(User.username == u_data["username"]))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                username=u_data["username"],
                phone=u_data["phone"],
                display_name=u_data["display_name"],
                password_hash=password_hash,
            )
            session.add(user)
        users[u_data["username"]] = user
    await session.commit()
    
    # Refresh users to get IDs
    for u in users.values():
        await session.refresh(u)
    return users

async def seed_contacts(session, users):
    """Add mutual contacts between seed users."""
    contact_pairs = [
        ("alice", "bob"),
        ("alice", "charlie"),
        ("alice", "emma"),
        ("bob", "charlie"),
        ("bob", "david"),
        ("charlie", "emma"),
        ("charlie", "frank"),
        ("david", "emma"),
    ]
    for u1_name, u2_name in contact_pairs:
        u1, u2 = users[u1_name], users[u2_name]
        # u1 -> u2
        res = await session.execute(
            select(Contact).where(Contact.user_id == u1.id, Contact.contact_user_id == u2.id)
        )
        if not res.scalar_one_or_none():
            session.add(Contact(user_id=u1.id, contact_user_id=u2.id))
        # u2 -> u1 (mutual)
        res = await session.execute(
            select(Contact).where(Contact.user_id == u2.id, Contact.contact_user_id == u1.id)
        )
        if not res.scalar_one_or_none():
            session.add(Contact(user_id=u2.id, contact_user_id=u1.id))
    await session.commit()

async def seed_conversations(session, users):
    # Direct Alice <-> Bob
    conv1 = await get_or_create_direct_conv(session, users["alice"], users["bob"])
    # Direct Charlie <-> Emma
    conv2 = await get_or_create_direct_conv(session, users["charlie"], users["emma"])
    # Direct Alice <-> Charlie
    conv4 = await get_or_create_direct_conv(session, users["alice"], users["charlie"])
    # Direct Bob <-> David
    conv5 = await get_or_create_direct_conv(session, users["bob"], users["david"])
    # Group Alice, Bob, Charlie (Alice is admin)
    conv3 = await get_or_create_group_conv(session, "Project Alpha", users["alice"], [users["bob"], users["charlie"]])
    
    return conv1, conv2, conv3, conv4, conv5

async def get_or_create_direct_conv(session, u1, u2):
    name = f"direct_{min(u1.username, u2.username)}_{max(u1.username, u2.username)}"
    result = await session.execute(select(Conversation).where(Conversation.name == name))
    conv = result.scalar_one_or_none()
    if not conv:
        conv = Conversation(type=ConversationType.DIRECT, name=name)
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
        m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role=MemberRole.MEMBER)
        m2 = ConversationMember(conversation_id=conv.id, user_id=u2.id, role=MemberRole.MEMBER)
        session.add_all([m1, m2])
        await session.commit()
    return conv

async def get_or_create_group_conv(session, group_name, admin_user, other_users):
    result = await session.execute(select(Conversation).where(Conversation.name == group_name, Conversation.type == ConversationType.GROUP))
    conv = result.scalar_one_or_none()
    if not conv:
        conv = Conversation(type=ConversationType.GROUP, name=group_name, created_by_id=admin_user.id)
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
        members = [ConversationMember(conversation_id=conv.id, user_id=admin_user.id, role=MemberRole.ADMIN)]
        for u in other_users:
            members.append(ConversationMember(conversation_id=conv.id, user_id=u.id, role=MemberRole.MEMBER))
        session.add_all(members)
        await session.commit()
    return conv

async def add_message(session, conv_id, sender_id, content, minutes_ago=0):
    """Helper to add a message if the conversation has no messages yet at that slot."""
    msg = Message(
        conversation_id=conv_id,
        sender_id=sender_id,
        content=content,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg

async def seed_messages(session, users, convs):
    conv1, conv2, conv3, conv4, conv5 = convs

    # Alice <-> Bob
    result = await session.execute(select(Message).where(Message.conversation_id == conv1.id))
    if not result.scalars().first():
        msgs = [
            ("alice", "Hey Bob! How's it going?"),
            ("bob", "Hey Alice! Doing great, thanks for asking."),
            ("alice", "Did you see the new Signal features they announced?"),
            ("bob", "Yeah! The story updates look interesting."),
            ("alice", "We should catch up this weekend"),
            ("bob", "Absolutely! Saturday works for me 👍"),
        ]
        for sender_name, content in msgs:
            msg = await add_message(session, conv1.id, users[sender_name].id, content)
            receipt = MessageReceipt(message_id=msg.id, user_id=users["bob"].id, status=ReceiptStatus.READ)
            session.add(receipt)
        await session.commit()

    # Charlie <-> Emma
    result = await session.execute(select(Message).where(Message.conversation_id == conv2.id))
    if not result.scalars().first():
        msgs = [
            ("charlie", "Emma, are you free tomorrow?"),
            ("emma", "Yes! What's up?"),
            ("charlie", "I wanted to discuss the project timeline"),
            ("emma", "Sure, let's do a call at 3pm"),
            ("charlie", "Perfect 👌"),
        ]
        for sender_name, content in msgs:
            await add_message(session, conv2.id, users[sender_name].id, content)

    # Group Alpha
    result = await session.execute(select(Message).where(Message.conversation_id == conv3.id))
    if not result.scalars().first():
        msgs = [
            ("alice", "Welcome to Project Alpha team! 🎉"),
            ("bob", "Hey team! Excited to be here"),
            ("charlie", "Same here! Let's ship something great"),
            ("alice", "Our first milestone is the auth system — done ✅"),
            ("bob", "Phase 2 messaging is next. Who's taking the backend?"),
            ("charlie", "I can handle the conversations API"),
            ("alice", "Great! I'll do the frontend UI"),
            ("bob", "I'll write the tests 🧪"),
        ]
        for sender_name, content in msgs:
            msg = await add_message(session, conv3.id, users[sender_name].id, content)
            # Mark messages as read by alice and delivered to charlie
            rec1 = MessageReceipt(message_id=msg.id, user_id=users["alice"].id, status=ReceiptStatus.READ)
            rec2 = MessageReceipt(message_id=msg.id, user_id=users["charlie"].id, status=ReceiptStatus.DELIVERED)
            session.add_all([rec1, rec2])
        await session.commit()

    # Alice <-> Charlie
    result = await session.execute(select(Message).where(Message.conversation_id == conv4.id))
    if not result.scalars().first():
        msgs = [
            ("charlie", "Alice, got a moment?"),
            ("alice", "Sure! What's up Charlie?"),
            ("charlie", "Quick question about the DB schema"),
            ("alice", "Of course, ask away"),
        ]
        for sender_name, content in msgs:
            await add_message(session, conv4.id, users[sender_name].id, content)

    # Bob <-> David
    result = await session.execute(select(Message).where(Message.conversation_id == conv5.id))
    if not result.scalars().first():
        msgs = [
            ("bob", "David! Long time no chat"),
            ("david", "Bob! Yeah it's been a while. How are things?"),
            ("bob", "Pretty good. Working on a Signal clone actually 😄"),
            ("david", "No way! That's awesome. Need any help?"),
            ("bob", "Always! Jump in anytime"),
        ]
        for sender_name, content in msgs:
            await add_message(session, conv5.id, users[sender_name].id, content)

async def seed():
    async with async_session_factory() as session:
        print("Seeding users...")
        users = await seed_users(session)
        print("Seeding contacts...")
        await seed_contacts(session, users)
        print("Seeding conversations...")
        convs = await seed_conversations(session, users)
        print("Seeding messages...")
        await seed_messages(session, users, convs)
        print("Seed data successfully populated.")

if __name__ == "__main__":
    asyncio.run(seed())
