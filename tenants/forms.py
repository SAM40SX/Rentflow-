
from django import forms
from accounts.models import User
from properties.models import Property
from .models import Tenant


class TenantRegistrationForm(forms.Form):

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username'
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )

    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter phone number'
        })
    )

    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create password'
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )

    def clean_username(self):
        username = self.cleaned_data['username']

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                'This username is already taken.'
            )

        return username

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError(
                    'Passwords do not match.'
                )

        return cleaned_data


class TenantAssignmentForm(forms.ModelForm):

    class Meta:
        model = Tenant
        fields = [
            'tenant_user',
            'property',
            'move_in_date',
            'monthly_rent',
            'deposit_amount'
        ]

        widgets = {
            'tenant_user': forms.Select(attrs={
                'class': 'form-control'
            }),

            'property': forms.Select(attrs={
                'class': 'form-control'
            }),

            'move_in_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),

            'monthly_rent': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter monthly rent'
            }),

            'deposit_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter deposit amount'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['tenant_user'].queryset = User.objects.filter(
            role='tenant',
            is_active=True,
            is_active_account=True
        )

        self.fields['property'].queryset = Property.objects.all()
