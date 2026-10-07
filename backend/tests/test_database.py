import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.models.user import User
from app.models.contact import Contact
from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember, MemberRole
from app.models.message import Message, MessageType
from app.models.message_receipt import MessageReceipt, ReceiptStatus
from app.core.security import hash_password

pytestmark = pytest.mark.asyncio

async def test_user_creation(db_session):
    u = User(username="testuser", password_hash=hash_password("pw"))
    db_session.add(u)
    await db_session.commit()
    assert u.id is not None
    assert u.created_at is not None

async def test_unique_username(db_session):
    u1 = User(username="uniqueuser", password_hash="pw")
    db_session.add(u1)
    await db_session.commit()
    
    u2 = User(username="uniqueuser", password_hash="pw2")
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

async def test_contact_relationship(db_session):
    u1 = User(username="contact1", password_hash="pw")
    u2 = User(username="contact2", password_hash="pw")
    db_session.add_all([u1, u2])
    await db_session.commit()
    
    c = Contact(user_id=u1.id, contact_user_id=u2.id)
    db_session.add(c)
    await db_session.commit()
    
    assert c.id is not None
    assert c.user_id == u1.id
    assert c.contact_user_id == u2.id

async def test_duplicate_contact(db_session):
    u1 = User(username="dup1", password_hash="pw")
    u2 = User(username="dup2", password_hash="pw")
    db_session.add_all([u1, u2])
    await db_session.commit()
    
    c1 = Contact(user_id=u1.id, contact_user_id=u2.id)
    db_session.add(c1)
    await db_session.commit()
    
    c2 = Contact(user_id=u1.id, contact_user_id=u2.id)
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

async def test_conversation_and_membership(db_session):
    u1 = User(username="convuser", password_hash="pw")
    db_session.add(u1)
    await db_session.commit()
    
    conv = Conversation(type=ConversationType.GROUP, name="Test Group", created_by_id=u1.id)
    db_session.add(conv)
    await db_session.commit()
    
    m = ConversationMember(conversation_id=conv.id, user_id=u1.id, role=MemberRole.ADMIN)
    db_session.add(m)
    await db_session.commit()
    assert m.id is not None

async def test_duplicate_membership(db_session):
    u1 = User(username="dupconvuser", password_hash="pw")
    db_session.add(u1)
    await db_session.commit()
    
    conv = Conversation(type=ConversationType.GROUP)
    db_session.add(conv)
    await db_session.commit()
    
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id)
    db_session.add(m1)
    await db_session.commit()
    
    m2 = ConversationMember(conversation_id=conv.id, user_id=u1.id)
    db_session.add(m2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

async def test_message_and_receipt(db_session):
    u1 = User(username="msguser1", password_hash="pw")
    u2 = User(username="msguser2", password_hash="pw")
    db_session.add_all([u1, u2])
    await db_session.commit()
    
    conv = Conversation(type=ConversationType.DIRECT)
    db_session.add(conv)
    await db_session.commit()
    
    msg = Message(conversation_id=conv.id, sender_id=u1.id, content="Hello")
    db_session.add(msg)
    await db_session.commit()
    
    assert msg.id is not None
    assert msg.conversation_id == conv.id
    
    receipt = MessageReceipt(message_id=msg.id, user_id=u2.id, status=ReceiptStatus.DELIVERED)
    db_session.add(receipt)
    await db_session.commit()
    
    assert receipt.id is not None

async def test_duplicate_receipt(db_session):
    u1 = User(username="recuser", password_hash="pw")
    db_session.add(u1)
    conv = Conversation(type=ConversationType.DIRECT)
    db_session.add(conv)
    await db_session.commit()
    
    msg = Message(conversation_id=conv.id, sender_id=u1.id, content="Hi")
    db_session.add(msg)
    await db_session.commit()
    
    r1 = MessageReceipt(message_id=msg.id, user_id=u1.id, status=ReceiptStatus.SENT)
    db_session.add(r1)
    await db_session.commit()
    
    r2 = MessageReceipt(message_id=msg.id, user_id=u1.id, status=ReceiptStatus.READ)
    db_session.add(r2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

async def test_reply_relationship(db_session):
    u1 = User(username="replyuser", password_hash="pw")
    db_session.add(u1)
    conv = Conversation(type=ConversationType.DIRECT)
    db_session.add(conv)
    await db_session.commit()
    
    msg1 = Message(conversation_id=conv.id, sender_id=u1.id, content="First")
    db_session.add(msg1)
    await db_session.commit()
    
    msg2 = Message(conversation_id=conv.id, sender_id=u1.id, content="Reply", reply_to_message_id=msg1.id)
    db_session.add(msg2)
    await db_session.commit()
    
    assert msg2.reply_to_message_id == msg1.id

async def test_seed_idempotency():
    # Calling seed multiple times does not throw IntegrityError
    from seed import seed
    await seed()
    await seed()
