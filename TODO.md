# TODO: Fix JWT role extraction for frontend

- [x] Step 1: Update accounts/models.py - Add ADMIN to User.Role.choices
- [x] Step 2: Add CustomTokenObtainPairSerializer to accounts/serializers.py
- [x] Step 3: Add CustomTokenObtainPairView to accounts/views.py
- [x] Step 4: Update accounts/urls.py to use custom view
- [x] Step 5: Test login and verify JWT payload includes role
- [x] Step 6: Migrate if needed and complete
