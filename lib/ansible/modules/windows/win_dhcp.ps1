#!powershell

# Copyright © 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: GPL-3.0-only
# Ansible Module by Joseph Zollo (jzollo@vmware.com)

#AnsibleRequires -CSharpUtil Ansible.Basic
#Requires -Module Ansible.ModuleUtils.CamelConversion
#Requires -Module Ansible.ModuleUtils.FileUtil
#Requires -Module Ansible.ModuleUtils.Legacy

$ErrorActionPreference = "Stop"

Function Convert-MacAddress {
    Param(
        [string]$mac
    )

    # Evaluate Length
    if ($mac.Length -eq 12) {
        # Insert Dashes
        $mac = $mac.Insert(2, "-").Insert(5, "-").Insert(8, "-").Insert(11, "-").Insert(14, "-")
        return $mac
    }
    elseif ($mac.Length -eq 17) {
        # Remove Dashes
        $mac = $mac -replace '-'
        return $mac
    }
    else {
        return $false
    }
}

Function Convert-ReturnValues {
    Param(
        $Object
    )

    $data = @{
        AddressState = $Object.AddressState
        ClientId     = $Object.ClientId
        IPAddress    = $Object.IPAddress.IPAddressToString
        ScopeId      = $Object.ScopeId.IPAddressToString
        Name         = $Object.Name
        Description  = $Object.Description
    }

    return $data
}

# Doesn't Support Check or Diff Mode
$params = Parse-Args -arguments $args -supports_check_mode $false
$check_mode = Get-AnsibleParam -obj $params -name "_ansible_check_mode" -type "bool" -default $false
$diff_mode = Get-AnsibleParam -obj $params -name "_ansible_diff" -type "bool" -default $false

# Client Config Params
$type = Get-AnsibleParam -obj $params -name "type" -type "str" -validateset ("reservation", "lease")
$ip = Get-AnsibleParam -obj $params -name "ip" -type "str"
$scope_id = Get-AnsibleParam -obj $params -name "scope_id" -type "str"
$mac = Get-AnsibleParam -obj $params -name "mac" -type "str"
$duration = Get-AnsibleParam -obj $params -name "duration" -type "int"
$dns_hostname = Get-AnsibleParam -obj $params -name "dns_hostname" -type "str"
$dns_regtype = Get-AnsibleParam -obj $params -name "dns_regtype" -type "str" -default "aptr" -validateset ("aptr", "a", "noreg")
$reservation_name = Get-AnsibleParam -obj $params -name "reservation_name" -type "str"
$description = Get-AnsibleParam -obj $params -name "description" -type "str"
$state = Get-AnsibleParam -obj $params -name "state" -type "str" -default "present" -validateset ("absent", "present")

# Result KVP
$result = @{
    changed = $false
}

# Parse Regtype
if ($dns_regtype) {
    Switch ($dns_regtype) {
        "aptr" { $dns_regtype = "AandPTR"; break }
        "a" { $dns_regtype = "A"; break }
        "noreg" { $dns_regtype = "NoRegistration"; break }
        default { $dns_regtype = "NoRegistration"; break }
    }
}

Try {
    # Import DHCP Server PS Module
    Import-Module DhcpServer
}
Catch {
    # Couldn't load the DhcpServer Module
    Fail-Json -obj $result -message "The DhcpServer module failed to load properly."
}


<#
# Determine if there is an existing lease
#>

if ($ip) {
    $current_lease = Get-DhcpServerv4Scope | Get-DhcpServerv4Lease | Where-Object IPAddress -eq $ip
}

# MacAddress was specified
if ($mac) {
    if (($mac = Convert-MacAddress -mac $mac) -eq $false) {
        Fail-Json -obj $result -message "The MAC Address is improperly formatted"
    }
    else {
        $current_lease = Get-DhcpServerv4Scope | Get-DhcpServerv4Lease | Where-Object ClientId -eq $mac
    }
}

# Determine if we retreived a lease

# Did we find a lease/reservation
if ($current_lease) {
    $current_lease_exists = $true
}
else {
    $current_lease_exists = $false
}

# If we found a lease, is it a reservation
if ($current_lease_exists -eq $true -and ($current_lease.AddressState -like "*Reservation*")) {
    $current_lease_reservation = $true
}
else {
    $current_lease_reservation = $false
}

# State: Absent
# Ensure the DHCP Lease/Reservation is not present
if ($state -eq "absent") {

    # Required: MAC or IP address
    if ((-not $mac) -and (-not $ip)) {
        $result.changed = $false
        Fail-Json -obj $result -message "The ip or mac parameter is required for state=absent"
    }

    # If the lease exists, we need to destroy it
    if ($current_lease_reservation -eq $true) {
        # Try to remove reservation
        Try {
            $current_lease | Remove-DhcpServerv4Reservation 
            $state_absent_removed = $true
        }
        Catch {
            $state_absent_removed = $false
        }
    } else {
        # Try to remove lease
        Try {
            $current_lease | Remove-DhcpServerv4Lease 
            $state_absent_removed = $true
        }
        Catch { 
            $state_absent_removed = $false
        }
    }

    # If the lease doesn't exist, our work here is done
    if ($current_lease_exists -eq $false) {
        $result.changed = $false
        Exit-Json -obj $result
    }

    # See if we removed the lease/reservation
    if ($state_absent_removed) {
        $result.changed = $true
        Exit-Json -obj $result
    }
    else {
        $result.lease = Convert-ReturnValues -Object $current_lease
        Fail-Json -obj $result -message "Could not remove lease/reservation"
    }
} 

# State: Present
# Ensure the DHCP Lease/Reservation is present, and consistent
if ($state -eq "present") {

    # Current lease exists, and is not a reservation
    if (($current_lease_reservation -eq $false) -and ($current_lease_exists -eq $true)) {
        if ($type -eq "reservation") {
            Try {
                # Update parameters
                $params = @{ }
                if ($mac) {
                    $params.ClientId = $mac
                }
                else {
                    $params.ClientId = $current_lease.ClientId
                }

                if ($description) {
                    $params.Description = $description
                }
                else {
                    $params.Description = $current_lease.Description
                }

                if ($reservation_name) {
                    $params.Name = $reservation_name
                }
                else {
                    $params.Name = $current_lease.ClientId + "-" + "res"
                }
    
                # Desired type is reservation
                $current_lease | Add-DhcpServerv4Reservation
                $current_reservation = Get-DhcpServerv4Reservation -ClientId $current_lease.ClientId -ScopeId $current_lease.ScopeId
                # Update the reservation with new values
                $current_reservation | Set-DhcpServerv4Reservation @params
                $reservation = Get-DhcpServerv4Reservation -ClientId $current_reservation.ClientId -ScopeId $current_reservation.ScopeId
                # Successful
                $result.changed = $true
                $result.lease = Convert-ReturnValues -Object $reservation
                Exit-Json -obj $result
            }
            Catch {
                $result.changed = $false
                Fail-Json -obj $result -message "Could not convert lease to a reservation"
            }
        }

        # Nothing needs to be done, already in the desired state
        if ($type -eq "lease") {
            $result.changed = $false
            $result.lease = Convert-ReturnValues -Object $current_lease
            Exit-Json -obj $result
        }
    }

    # Current lease exists, and is a reservation
    if (($current_lease_reservation -eq $true) -and ($current_lease_exists -eq $true)) {
        if ($type -eq "lease") {
            Try {
                # Save Lease Data
                $lease = $current_lease
                # Desired type is a lease, remove & recreate
                $current_lease | Remove-DhcpServerv4Reservation
                # Create new lease
                Add-DhcpServerv4Lease -Name $lease.Name -IPAddress $lease.IPAddress -ClientId $lease.ClientId -Description $lease.Description -ScopeId $lease.ScopeId
                # Get the lease we just created
                $new_lease = Get-DhcpServerv4Lease -ClientId $lease.ClientId -ScopeId $lease.ScopeId
                # Successful
                $result.changed = $true
                $result.lease = Convert-ReturnValues -Object $new_lease
                Exit-Json -obj $result
            }
            Catch {
                $result.changed = $false
                Fail-Json -obj $result -message "Could not convert reservation to lease"
            }
        }

        # Already in the desired state
        if ($type -eq "reservation") {

            # Update parameters
            $params = @{ }
            if ($mac) {
                $params.ClientId = $mac
            }
            else {
                $params.ClientId = $current_lease.ClientId
            }

            if ($description) {
                $params.Description = $description
            }
            else {
                $params.Description = $current_lease.Description
            }

            if ($reservation_name) {
                $params.Name = $reservation_name
            }

            # Update the reservation with new values
            $current_lease | Set-DhcpServerv4Reservation @params
            $reservation = Get-DhcpServerv4Reservation -ClientId $current_lease.ClientId -ScopeId $current_lease.ScopeId
            # Successful
            $result.changed = $true
            $result.lease = Convert-ReturnValues -Object $reservation
            Exit-Json -obj $result
        }
    }

    # Lease Doesn't Exist - Create
    if ($current_lease_exists -eq $false) {

        # Required: MAC and IP address
        if ((-not $mac) -or (-not $ip)) {
            $result.changed = $false
            Fail-Json -obj $result -message "The ip and mac parameters are required for state=present"
        }

        # Required: Scope ID
        if (-not $scope_id) {
            $result.changed = $false
            Fail-Json -obj $result -message "The scope_id parameter is required for state=present"
        }

        # Required Parameters
        $lease_params = @{
            ClientId     = $mac
            IPAddress    = $ip
            ScopeId      = $scope_id
            AddressState = 'Active'
            Confirm      = $false
        }

        if ($duration) {
            $lease_params.LeaseExpiryTime = (Get-Date).AddDays($duration)
        }

        if ($dns_hostname) {
            $lease_params.HostName = $dns_hostname
        }

        if ($dns_regtype) {
            $lease_params.DnsRR = $dns_regtype
        }

        if ($description) {
            $lease_params.Description = $description
        }

        # Create Lease
        Try {
            # Create lease based on parameters
            Add-DhcpServerv4Lease @lease_params
            # Retreive the lease
            $lease = Get-DhcpServerv4Lease -ClientId $mac -ScopeId $scope_id

            # If lease is the desired type
            if ($type -eq "lease") {
                $result.changed = $true
                $result.lease = Convert-ReturnValues -Object $lease
                Exit-Json -obj $result
            }
        }
        Catch {
            # Failed to create lease
            $result.changed = $false
            Fail-Json -obj $result -message "Could not create DHCP lease"
        }

        # Create Reservation
        Try {
            # If reservation is the desired type
            if ($type -eq "reservation") {
                if ($reservation_name) {
                    $lease_params.Name = $reservation_name
                }
                else {
                    $lease_params.Name = $mac + "_" + "pc"
                }

                # Convert to Reservation
                $lease | Add-DhcpServerv4Reservation
                # Get DHCP reservation object
                $reservation = Get-DhcpServerv4Reservation -ClientId $mac -ScopeId $scope_id
                $result.changed = $true
                $result.lease = Convert-ReturnValues -Object $reservation
                Exit-Json -obj $result
            }
        }
        Catch {
            # Failed to create reservation
            $result.changed = $false
            Fail-Json -obj $result -message "Could not create DHCP reservation"
        }
    }
}

# Exit, Return Result
Exit-Json -obj $result