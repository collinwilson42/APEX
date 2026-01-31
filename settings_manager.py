"""
MT5 META AGENT V11 - SETTINGS MANAGER
Handles all user-configurable parameters with validation
V11.2 - Centralized configuration management
"""

import sqlite3
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


class SettingsManager:
    """
    Centralized settings management system
    Handles loading, validation, and persistence of all user configurations
    """
    
    def __init__(self, db_path: str = 'mt5_intelligence.db'):
        self.db_path = db_path
        self.cache = {}
        self.load_all_settings()
    
    def load_all_settings(self) -> Dict[str, Any]:
        """Load all settings from database into cache"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM settings")
            rows = cursor.fetchall()
            
            self.cache = {}
            for row in rows:
                key = row['setting_key']
                value = self._parse_value(row['setting_value'], row['setting_type'])
                self.cache[key] = {
                    'value': value,
                    'type': row['setting_type'],
                    'category': row['category'],
                    'tier': row['tier'],
                    'description': row['description'],
                    'default': self._parse_value(row['default_value'], row['setting_type']),
                    'min': self._parse_value(row['min_value'], row['setting_type']) if row['min_value'] else None,
                    'max': self._parse_value(row['max_value'], row['setting_type']) if row['max_value'] else None
                }
            
            conn.close()
            return self.cache
            
        except Exception as e:
            print(f"[SETTINGS] Error loading settings: {e}")
            return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value by key
        Returns default if key not found
        """
        if key in self.cache:
            return self.cache[key]['value']
        return default
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings as simple key-value dictionary"""
        return {key: data['value'] for key, data in self.cache.items()}
    
    def get_by_category(self, category: str) -> Dict[str, Any]:
        """Get all settings for a specific category"""
        return {
            key: data 
            for key, data in self.cache.items() 
            if data['category'] == category
        }
    
    def get_by_tier(self, tier: int) -> Dict[str, Any]:
        """Get all settings for a specific tier (1-4)"""
        return {
            key: data 
            for key, data in self.cache.items() 
            if data['tier'] == tier
        }
    
    def set(self, key: str, value: Any) -> Tuple[bool, str]:
        """
        Set setting value with validation
        Returns (success, message)
        """
        if key not in self.cache:
            return False, f"Setting '{key}' not found"
        
        setting_info = self.cache[key]
        setting_type = setting_info['type']
        
        # Validate type
        try:
            validated_value = self._validate_type(value, setting_type)
        except ValueError as e:
            return False, f"Type validation failed: {str(e)}"
        
        # Validate range
        min_val = setting_info['min']
        max_val = setting_info['max']
        
        if min_val is not None and validated_value < min_val:
            return False, f"Value {validated_value} is below minimum {min_val}"
        
        if max_val is not None and validated_value > max_val:
            return False, f"Value {validated_value} exceeds maximum {max_val}"
        
        # Save to database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE settings 
                SET setting_value = ?, updated_at = ?
                WHERE setting_key = ?
            """, (self._serialize_value(validated_value, setting_type), 
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                  key))
            
            conn.commit()
            conn.close()
            
            # Update cache
            self.cache[key]['value'] = validated_value
            
            return True, f"Setting '{key}' updated successfully"
            
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def set_multiple(self, settings_dict: Dict[str, Any]) -> Dict[str, Tuple[bool, str]]:
        """
        Set multiple settings at once
        Returns dictionary of results for each key
        """
        results = {}
        for key, value in settings_dict.items():
            results[key] = self.set(key, value)
        return results
    
    def reset(self, key: str) -> Tuple[bool, str]:
        """Reset setting to default value"""
        if key not in self.cache:
            return False, f"Setting '{key}' not found"
        
        default_value = self.cache[key]['default']
        return self.set(key, default_value)
    
    def reset_all(self) -> Dict[str, Tuple[bool, str]]:
        """Reset all settings to defaults"""
        results = {}
        for key in self.cache.keys():
            results[key] = self.reset(key)
        return results
    
    def reset_category(self, category: str) -> Dict[str, Tuple[bool, str]]:
        """Reset all settings in a category to defaults"""
        results = {}
        category_settings = self.get_by_category(category)
        for key in category_settings.keys():
            results[key] = self.reset(key)
        return results
    
    def export_config(self) -> str:
        """Export current configuration as JSON string"""
        config = {
            'version': 'V11.2',
            'exported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'settings': {key: data['value'] for key, data in self.cache.items()}
        }
        return json.dumps(config, indent=2)
    
    def import_config(self, config_json: str) -> Tuple[bool, str, Dict]:
        """
        Import configuration from JSON string
        Returns (success, message, results_dict)
        """
        try:
            config = json.loads(config_json)
            
            if 'settings' not in config:
                return False, "Invalid config format: missing 'settings' key", {}
            
            results = self.set_multiple(config['settings'])
            
            success_count = sum(1 for success, _ in results.values() if success)
            total_count = len(results)
            
            message = f"Imported {success_count}/{total_count} settings successfully"
            return True, message, results
            
        except json.JSONDecodeError as e:
            return False, f"JSON parsing error: {str(e)}", {}
        except Exception as e:
            return False, f"Import error: {str(e)}", {}
    
    def get_categories(self) -> List[str]:
        """Get list of all setting categories"""
        return list(set(data['category'] for data in self.cache.values()))
    
    def get_metadata(self, key: str) -> Optional[Dict]:
        """Get full metadata for a setting"""
        return self.cache.get(key, None)
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    def _parse_value(self, value_str: str, value_type: str) -> Any:
        """Parse string value from database based on type"""
        if value_str is None:
            return None
        
        if value_type == 'int':
            return int(value_str)
        elif value_type == 'float':
            return float(value_str)
        elif value_type == 'bool':
            return value_str.lower() == 'true'
        else:  # str
            return value_str
    
    def _validate_type(self, value: Any, expected_type: str) -> Any:
        """Validate and convert value to expected type"""
        if expected_type == 'int':
            return int(value)
        elif expected_type == 'float':
            return float(value)
        elif expected_type == 'bool':
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() == 'true'
            return bool(value)
        else:  # str
            return str(value)
    
    def _serialize_value(self, value: Any, value_type: str) -> str:
        """Convert value to string for database storage"""
        if value_type == 'bool':
            return 'true' if value else 'false'
        return str(value)


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("SETTINGS MANAGER TEST")
    print("="*70)
    
    # Initialize manager
    manager = SettingsManager()
    
    print(f"\n✓ Loaded {len(manager.cache)} settings")
    
    # Test get
    print(f"\nTest GET:")
    print(f"  user_view_rows = {manager.get('user_view_rows')}")
    print(f"  ath_lookback_bars = {manager.get('ath_lookback_bars')}")
    print(f"  auto_refresh_enabled = {manager.get('auto_refresh_enabled')}")
    
    # Test set with validation
    print(f"\nTest SET with validation:")
    success, msg = manager.set('user_view_rows', 25)
    print(f"  Set user_view_rows=25: {success} - {msg}")
    
    success, msg = manager.set('user_view_rows', 100)  # Should fail (max = 50)
    print(f"  Set user_view_rows=100: {success} - {msg}")
    
    # Test get by category
    print(f"\nTest GET BY CATEGORY:")
    display_settings = manager.get_by_category('display')
    print(f"  Found {len(display_settings)} display settings:")
    for key in list(display_settings.keys())[:3]:
        print(f"    - {key}")
    
    # Test export
    print(f"\nTest EXPORT:")
    config_json = manager.export_config()
    print(f"  Exported {len(config_json)} characters")
    
    print("\n" + "="*70)
    print("✓ Settings manager test complete")
    print("="*70)
