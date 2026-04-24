from django.db import models
from customers.models import Client

class B2BConnection(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    requester = models.ForeignKey(Client, related_name='outgoing_connections', on_delete=models.CASCADE)
    receiver = models.ForeignKey(Client, related_name='incoming_connections', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('requester', 'receiver')
        # Since this is a shared app, these tables will be created in the public schema by django-tenants.

    def __str__(self):
        return f"{self.requester.schema_name} -> {self.receiver.schema_name} ({self.status})"


class B2BMessage(models.Model):
    connection = models.ForeignKey(B2BConnection, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(Client, related_name='sent_b2b_messages', on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Msg from {self.sender.schema_name} at {self.timestamp}"


class B2BGroup(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='created_b2b_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class B2BGroupMember(models.Model):
    group = models.ForeignKey(B2BGroup, on_delete=models.CASCADE, related_name='members')
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='b2b_group_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'tenant')

class B2BGroupMessage(models.Model):
    group = models.ForeignKey(B2BGroup, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='sent_b2b_group_messages')
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
