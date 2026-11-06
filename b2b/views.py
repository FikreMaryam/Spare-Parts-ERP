from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import connection

from customers.models import Client
from .models import B2BConnection, B2BMessage

def _get_current_tenant():
    schema = getattr(connection, 'schema_name', 'public')
    tenant, _ = Client.objects.get_or_create(schema_name=schema, defaults={'name': 'Main Shop'})
    return schema, tenant

@login_required
def network_home(request):
    """Shows active and pending connections"""
    current_schema, current_tenant = _get_current_tenant()

    # Connections where we requested
    outgoing_pending = B2BConnection.objects.filter(requester=current_tenant, status='pending')
    # Connections where they requested us
    incoming_pending = B2BConnection.objects.filter(receiver=current_tenant, status='pending')
    
    # Active connections
    active_connections = B2BConnection.objects.filter(
        Q(requester=current_tenant) | Q(receiver=current_tenant),
        status='accepted'
    )

    return render(request, 'b2b/network.html', {
        'current_tenant': current_tenant,
        'outgoing_pending': outgoing_pending,
        'incoming_pending': incoming_pending,
        'active_connections': active_connections,
    })

@login_required
def request_connection(request):
    if request.method == 'POST':
        target_username = request.POST.get('shop_name', '').strip().lower()
        current_schema, current_tenant = _get_current_tenant()
        
        if target_username == current_schema:
            messages.error(request, "You cannot connect to yourself.")
            return redirect('b2b:network_home')
            
        try:
            target_tenant = Client.objects.exclude(schema_name='public').get(schema_name=target_username)
            
            # Check if connection already exists in either direction
            exists = B2BConnection.objects.filter(
                Q(requester=current_tenant, receiver=target_tenant) |
                Q(requester=target_tenant, receiver=current_tenant)
            ).exists()
            
            if exists:
                messages.warning(request, "A connection request or active connection already exists with this shop.")
            else:
                B2BConnection.objects.create(
                    requester=current_tenant,
                    receiver=target_tenant,
                    status='pending'
                )
                messages.success(request, f"Connection request sent to '{target_tenant.name or target_tenant.schema_name}'!")
                
        except Client.DoesNotExist:
            messages.error(request, f"Shop '{target_username}' not found on the network.")
            
    return redirect('b2b:network_home')

@login_required
def accept_connection(request, connection_id):
    current_schema, current_tenant = _get_current_tenant()
    
    conn = get_object_or_404(B2BConnection, id=connection_id, receiver=current_tenant, status='pending')
    conn.status = 'accepted'
    conn.save()
    messages.success(request, f"You are now connected with {conn.requester.schema_name}!")
    
    return redirect('b2b:network_home')

@login_required
def b2b_chat(request, connection_id):
    current_schema, current_tenant = _get_current_tenant()
    
    conn = get_object_or_404(B2BConnection, id=connection_id, status='accepted')
    
    # Ensure current tenant is part of this connection
    if conn.requester != current_tenant and conn.receiver != current_tenant:
        messages.error(request, "You are not authorized to view this chat.")
        return redirect('b2b:network_home')
        
    other_tenant = conn.receiver if conn.requester == current_tenant else conn.requester

    if request.method == 'POST':
        text = request.POST.get('message', '').strip()
        if text:
            B2BMessage.objects.create(
                connection=conn,
                sender=current_tenant,
                text=text
            )
            return redirect('b2b:b2b_chat', connection_id=conn.id)
            
    messages_list = conn.messages.all()
    
    return render(request, 'b2b/chat.html', {
        'b2b_connection': conn,
        'other_tenant': other_tenant,
        'current_tenant': current_tenant,
        'chat_messages': messages_list
    })

