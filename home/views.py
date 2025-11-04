from django.shortcuts import render , redirect ,  get_object_or_404
from .forms import VisitorForm , HealthDataForm
from .models import Visitor , HealthData
from django.http import JsonResponse
from ex.models import ExerciseSession
from django.urls import reverse
from django.shortcuts import redirect
from django.db.models import Avg
from django.urls import reverse
from django.http import HttpResponseForbidden
import json


  

def visitor_registration(request):
    if request.method == 'POST':
        form = VisitorForm(request.POST, request.FILES)
        if form.is_valid():
            visitor = form.save(commit=False)

            # optional: you can override or track anything here
            # visitor.unique_id = uuid.uuid4()  # not needed if model handles it
            visitor.save()

            # store visitor ID in session
            request.session['visitor_id'] = visitor.id
            request.session['unique_token'] = str(visitor.unique_id)  
            return redirect('home')
    else:
        form = VisitorForm()

    return render(request, 'home/visitor_registration.html', {'form': form})


def home(request):
    visitor_id = request.session.get("visitor_id")

    # Check if session visitor exists
    if visitor_id:
        try:
            visitor = Visitor.objects.get(id=visitor_id)
        except Visitor.DoesNotExist:
            # Visitor was deleted — reset session and go to registration
            del request.session["visitor_id"]
            return redirect("visitor_registration")

        # Render home page if visitor exists
        return render(request, "home/home.html", {"visitor": visitor})

    # No visitor found in session — go to registration form
    return redirect("visitor_registration")


def health_journal_view(request):
    visitor_id = request.session.get("visitor_id")
    if not visitor_id:
        # if no visitor session → force them to register first
        return redirect("visitor_registration")

    visitor = get_object_or_404(Visitor, id=visitor_id)
    entries = visitor.health_entries.order_by("-created_at")

    # Are we editing something?
    edit_id = request.GET.get("edit")
    entry_to_edit = None
    edit_form = None

    if edit_id:
        entry_to_edit = get_object_or_404(HealthData, id=edit_id, visitor=visitor)
        initial = entry_to_edit.__dict__
        initial["symptoms"] = entry_to_edit.symptom_list
        edit_form = HealthDataForm(instance=entry_to_edit, initial=initial)

    if request.method == "POST":
        # Editing existing entry
        if "edit_entry_id" in request.POST:
            entry = get_object_or_404(HealthData, id=request.POST["edit_entry_id"], visitor=visitor)
            form = HealthDataForm(request.POST, instance=entry)
            if form.is_valid():
                updated = form.save(commit=False)
                updated.symptoms = ", ".join(form.cleaned_data["symptoms"])
                updated.save()
                return redirect("journal")

        # Creating new entry
        else:
            form = HealthDataForm(request.POST)
            if form.is_valid():
                entry = form.save(commit=False)
                entry.visitor = visitor
                entry.symptoms = ", ".join(form.cleaned_data["symptoms"])
                entry.save()
                return redirect("journal")
    else:
        form = HealthDataForm()

    return render(request, "home/journal.html", {
        "visitor": visitor,
        "entries": entries,
        "form": form,
        "edit_form": edit_form,
        "entry_to_edit": entry_to_edit,
    })


def delete_entry(request, pk):
    visitor_id = request.session.get("visitor_id")
    if not visitor_id:
        return redirect("visitor_registration")

    visitor = get_object_or_404(Visitor, id=visitor_id)
    entry = get_object_or_404(HealthData, pk=pk)

    # Check ownership — only delete if entry belongs to the visitor
    if entry.visitor != visitor:
        return HttpResponseForbidden("You are not allowed to delete this entry.")

    entry.delete()
    return redirect("journal")



def health_tracker(request, visitor_id):
    session_visitor_id = request.session.get("visitor_id")
    if not session_visitor_id:
        return redirect("visitor_registration")

    # Only allow access to own data
    if int(visitor_id) != int(session_visitor_id):
        return HttpResponseForbidden("You are not allowed to view this page.")

    visitor = get_object_or_404(Visitor, id=session_visitor_id)
    health_entries = visitor.health_entries.order_by('created_at')
    exercise_sessions = ExerciseSession.objects.filter(visitor=visitor)
    
    # Weight and Energy Data
    weight_data = [
        {'date': entry.created_at.strftime('%Y-%m-%d'), 'weight': float(entry.weight or 0)}
        for entry in health_entries if entry.weight
    ]
    energy_data = [
        {'date': entry.created_at.strftime('%Y-%m-%d'), 'energy': entry.energy}
        for entry in health_entries if entry.energy
    ]

    # Pose Accuracy (average confidence per session)
    pose_accuracy_data = []
    for session in exercise_sessions:
        avg_conf = session.pose_logs.aggregate(avg_conf=Avg('confidence'))['avg_conf']
        if avg_conf is not None:
            pose_accuracy_data.append({
                'date': session.started_at.strftime('%Y-%m-%d'),
                'pose': session.target_pose,
                'confidence': round(avg_conf * 100, 2)
            })

    context = {
        'visitor': visitor,
        'health_entries': health_entries,
        'exercise_sessions': exercise_sessions,
        'weight_data': weight_data,
        'energy_data': energy_data,
        'pose_accuracy_data': pose_accuracy_data,
    }
    return render(request, 'home/health_tracker.html', context)
