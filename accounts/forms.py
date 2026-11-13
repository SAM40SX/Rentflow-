
from django import forms
from .models import User
import re


# PHONE NUMBER VALIDATION
def validate_phone_number(value):
    value = (value or '').strip()

    if not value:
        return value

    # Allow digits only, with an optional leading +.
    if not re.fullmatch(r'\+?[0-9]+', value):
        raise forms.ValidationError(
            'Phone number must contain numbers only. '
            'You may use a leading + for the country code.'
        )

    # Check that the number has a reasonable length.
    digits = value.lstrip('+')

    if not 9 <= len(digits) <= 15:
        raise forms.ValidationError(
            'Enter a valid phone number between 9 and 15 digits.'
        )

    return value


# TENANT PROFILE FORM
class TenantProfileForm(forms.ModelForm):

    class Meta:
        model = User

        fields = [
            'first_name',
            'last_name',
            'email',
            'phone_number',
        ]

        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your first name'
            }),

            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your last name'
            }),

            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your email address'
            }),

            'phone_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. 0712345678',
                'type': 'tel',
                'inputmode': 'numeric',
                'pattern': r'\+?[0-9]+',
                'title': 'Enter numbers only, with an optional leading +'
            }),
        }

    def clean_phone_number(self):
        return validate_phone_number(
            self.cleaned_data.get('phone_number')
        )


# TENANT REGISTRATION FORM
class TenantRegistrationForm(forms.ModelForm):

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a password'
        })
    )

    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm your password'
        })
    )

    class Meta:
        model = User

        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'phone_number',
        ]

        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Choose a username'
            }),

            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your first name'
            }),

            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your last name'
            }),

            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your email address'
            }),

            'phone_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. 0712345678',
                'type': 'tel',
                'inputmode': 'numeric',
                'pattern': r'\+?[0-9]+',
                'title': 'Enter numbers only, with an optional leading +'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists.'
            )

        return email

    def clean_phone_number(self):
        return validate_phone_number(
            self.cleaned_data.get('phone_number')
        )

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                'The passwords do not match.'
            )

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)

        # Public registration can only create tenant accounts.
        user.role = 'tenant'

        # New accounts require administrator approval.
        user.is_active = False
        user.is_active_account = False

        # Securely hash the password.
        user.set_password(self.cleaned_data['password1'])

        if commit:
            user.save()

        return user
