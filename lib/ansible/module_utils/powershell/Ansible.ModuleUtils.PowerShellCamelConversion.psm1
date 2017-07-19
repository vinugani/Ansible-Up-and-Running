# Copyright (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# used by Convert-DictToSnakeCase to convert a string in camelCase
# format to snake_case
Function Convert-StringToSnakeCase($string) {
    # cope with pluralized abbreaviations such as TargetGroupARNs
    if ($string -cmatch "[A-Z]{3,}s") {
        $replacement_string = $string -creplace $matches[0], "_$($matches[0].ToLower())"

        # handle when there was nothing before the plural pattern
        if ($replacement_string.StartsWith("_") -and -not $string.StartsWith("_")) {
            $replacement_string = $replacement_string.Substring(1)            
        }
        $string = $replacement_string
    }
    $string = $string -creplace "(.)([A-Z][a-z]+)", '$1_$2'
    $string = $string -creplace "([a-z0-9])([A-Z])", '$1_$2'
    $string = $string.ToLower()

    return $string
}

# used by Convert-DictToSnakeCase to covert list entries from camelCase
# to snake_case
Function Convert-ListToSnakeCase($list) {
    $snake_list = [System.Collections.ArrayList]@()
    foreach ($value in $list) {
        if ($value -is [Hashtable]) {
            $new_value = Convert-DictToSnakeCase -dict $value
        } elseif ($value -is [Array]) {
            $new_value = Convert-ListToSnakeCase -list $value
        } elseif ($value -is [String]) {
            $new_value = Convert-StringToSnakeCase -string $value
        } else {
            $new_value = $value
        }
        $snake_list.Add($new_value) | Out-Null
    }

    return $snake_list
}

# converts a dict/hashtable keys from camelCase to snake_case
# this is to keep the return values consistent with the Ansible
# way of working.
Function Convert-DictToSnakeCase($dict) {
    $snake_dict = @{}
    foreach ($dict_entry in $dict.GetEnumerator()) {
        $key = $dict_entry.Key
        $snake_key = Convert-StringToSnakeCase -string $key

        $value = $dict_entry.Value
        if ($value -is [Hashtable]) {
            $snake_dict.$snake_key = Convert-DictToSnakeCase -dict $value          
        } elseif ($value -is [Array]) {
            $snake_dict.$snake_key = Convert-ListToSnakeCase -list $value
        } elseif ($value -is [String]) {
            $snake_dict.$snake_key = Convert-StringToSnakeCase -string $value
        } else {
            $snake_dict.$snake_key = $value
        }
    }

    return $snake_dict
}

# this line must stay at the bottom to ensure all defined module parts are exported
Export-ModuleMember -Alias * -Function * -Cmdlet *
