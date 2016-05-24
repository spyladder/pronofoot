from django import forms

class AccountCreationForm(forms.Form):
    username = forms.CharField(label="Pseudo", max_length=30)
    email = forms.EmailField(label="Adresse mail")
    password = forms.CharField(label="Mot de passe", max_length=20, widget=forms.PasswordInput)


class AccountLoginForm(forms.Form):
    username = forms.CharField(label="Pseudo", max_length=30)
    password = forms.CharField(label="Mot de passe", max_length=20, widget=forms.PasswordInput)


class PronosticForm(forms.Form):
    prono = forms.IntegerField(required=False, widget=forms.HiddenInput())
    match = forms.IntegerField(required=False, widget=forms.HiddenInput())
    score_a = forms.IntegerField(min_value=0)
    score_b = forms.IntegerField(min_value=0)
    winner = forms.CharField(widget=forms.Select())
