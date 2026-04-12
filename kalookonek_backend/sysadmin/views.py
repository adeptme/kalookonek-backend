from django.shortcuts import render
from django.http import HttpResponse 

# Create your views here.
def dashboard(request):
    pass

def admin(request):
    if request.method == 'GET':
        pass
    elif request.method == 'UPDATE':
        pass

def all_users(request):
    pass

def user(request, id):
    if request.method == 'GET':
        pass
    elif request.method == 'UPDATE':
        pass
    elif request.method == 'DELETE':
        pass

def announcements(request):
    pass

def announcement(request, id):
    if request.method == 'GET':
        pass
    elif request.method == 'UPDATE':
        pass
    elif request.method == 'DELETE':
        pass

def appointment_request(request):
    if request.method == 'GET':
        pass
    elif request.method == 'POST':
        pass

def refill_requests(request):
    if request.method == 'GET':
        pass
    elif request.method == 'POST':
        pass
    elif request.method == 'UPDATE':
        pass