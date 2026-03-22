"""
Profile Manager
==============

Cookie profile file I/O with key-based matching and auto-naming.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional, Callable


class ProfileManager:
    """
    Manages cookie profiles stored in a JSON file.
    
    Profiles are stored as a JSON array of objects. Each profile has:
    - A "name" field for identification
    - Cookie fields (user-defined)
    - A "last_updated" timestamp (auto-generated)
    
    Profile matching uses a configurable "key" field (e.g., "user_id")
    to find existing profiles for update vs. creating new ones.
    
    File format:
        [
          {
            "name": "profile1",
            "cf_clearance": "...",
            "sso": "...",
            "user_id": "abc-123",
            "last_updated": "2026-03-21 15:30:00"
          }
        ]
    
    Args:
        file_path: Path to the JSON profiles file.
        key_field: Field used to identify unique profiles (e.g., "user_id").
    """
    
    def __init__(self, file_path: str, key_field: str):
        self._file_path = Path(file_path)
        self._key_field = key_field
    
    @property
    def file_path(self) -> Path:
        """Return the profiles file path."""
        return self._file_path
    
    @property
    def key_field(self) -> str:
        """Return the key field name."""
        return self._key_field
    
    def load_profiles(self) -> list[dict]:
        """
        Load profiles from the JSON file.
        
        Handles migration from legacy dict format to list format.
        
        Returns:
            List of profile dicts, or empty list if file doesn't exist.
        """
        if not self._file_path.exists():
            return []
        
        try:
            text = self._file_path.read_text(encoding="utf-8")
            data = json.loads(text)
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Migrate dict format to list format
                return self._migrate_dict_to_list(data)
            
            return []
            
        except (json.JSONDecodeError, OSError):
            return []
    
    def _migrate_dict_to_list(self, data: dict) -> list[dict]:
        """
        Migrate legacy dict format to list format.
        
        Legacy format was either:
        - Single profile: {"sso": "...", "cf_clearance": "...", ...}
        - Named profiles: {"name1": {...}, "name2": {...}}
        
        Args:
            data: Dict-format profile data.
            
        Returns:
            List-format profile data.
        """
        profiles = []
        
        # Check if it's a single profile (has cookie fields directly)
        if any(k in data for k in ["sso", "cf_clearance", "sessionid", "csrftoken"]):
            profiles.append({"name": "default", **data})
        else:
            # Named profiles dict
            for name, profile_data in data.items():
                if isinstance(profile_data, dict):
                    profiles.append({"name": name, **profile_data})
        
        return profiles
    
    def find_profile_by_key(self, key_value: str) -> Optional[dict]:
        """
        Find a profile that matches the given key value.
        
        Args:
            key_value: Value to match against the key field.
            
        Returns:
            The matching profile dict, or None if not found.
        """
        profiles = self.load_profiles()
        
        for profile in profiles:
            if isinstance(profile, dict) and profile.get(self._key_field) == key_value:
                return profile
        
        return None
    
    def find_profile_name_by_key(self, key_value: str) -> Optional[str]:
        """
        Find the profile name that matches the given key value.
        
        Args:
            key_value: Value to match against the key field.
            
        Returns:
            The profile name, or None if not found.
        """
        profile = self.find_profile_by_key(key_value)
        return profile.get("name") if profile else None
    
    def generate_profile_name(self, profiles: Optional[list[dict]] = None) -> str:
        """
        Generate a unique profile name (profile1, profile2, etc.).
        
        Args:
            profiles: Existing profiles list. If None, loads from file.
            
        Returns:
            A new unique profile name.
        """
        if profiles is None:
            profiles = self.load_profiles()
        
        existing_names = {
            p.get("name") for p in profiles 
            if isinstance(p, dict) and p.get("name")
        }
        
        i = 1
        while f"profile{i}" in existing_names:
            i += 1
        
        return f"profile{i}"
    
    def save_profile(
        self,
        profile_name: str,
        cookies: dict[str, str],
        extra_fields: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Save or update a profile in the JSON file.
        
        If a profile with the same name exists, it's updated.
        Otherwise, a new profile is appended.
        
        Uses atomic write (write to .tmp, then os.replace) to prevent
        corruption if interrupted.
        
        Args:
            profile_name: Name of the profile.
            cookies: Dict of cookie field names to values.
            extra_fields: Optional additional fields to save.
        """
        # Ensure parent directory exists
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        
        profiles = self.load_profiles()
        
        # Find existing profile or create new
        target_profile = None
        for p in profiles:
            if isinstance(p, dict) and p.get("name") == profile_name:
                target_profile = p
                break
        
        if target_profile is None:
            target_profile = {"name": profile_name}
            profiles.append(target_profile)
        
        # Update cookie fields
        target_profile.update(cookies)
        
        # Update extra fields if provided
        if extra_fields:
            target_profile.update(extra_fields)
        
        # Set timestamp
        target_profile["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Sort by last_updated (most recent first)
        profiles.sort(
            key=lambda p: p.get("last_updated", "1970-01-01 00:00:00"),
            reverse=True
        )
        
        # Atomic write
        tmp_path = self._file_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(profiles, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(str(tmp_path), str(self._file_path))
    
    def upsert_profile(
        self,
        cookies: dict[str, str],
        auto_name: bool = False,
        prompt_fn: Optional[Callable[[str], str]] = None,
    ) -> str:
        """
        Insert or update a profile based on the key field value.
        
        If a profile with matching key_field value exists, updates it.
        Otherwise, creates a new profile with auto-generated or prompted name.
        
        Args:
            cookies: Dict of cookie field names to values.
            auto_name: If True, auto-generate names for new profiles.
            prompt_fn: Optional function to prompt for profile name.
                       Signature: prompt_fn(message: str) -> str
        
        Returns:
            The profile name that was used.
        """
        key_value = cookies.get(self._key_field)
        
        # Try to find existing profile
        profile_name = self.find_profile_name_by_key(key_value) if key_value else None
        
        if not profile_name:
            # New profile - determine name
            if auto_name:
                profile_name = self.generate_profile_name()
            elif prompt_fn:
                profile_name = prompt_fn(f"Enter name for new profile (key: {key_value}): ")
                if not profile_name.strip():
                    profile_name = self.generate_profile_name()
            else:
                profile_name = self.generate_profile_name()
        
        self.save_profile(profile_name, cookies)
        return profile_name
