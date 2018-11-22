#!powershell

# Copyright: (c) 2018, Wojciech Sciesinski <wojciech[at]sciesinski[dot]net>
# Copyright: (c) 2017, Daniele Lazzari <lazzari@mailup.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

#Requires -Module Ansible.ModuleUtils.Legacy

# win_psmodule (Windows PowerShell modules Additions/Removals/Updates)

$params = Parse-Args -arguments $args -supports_check_mode $true

$name = Get-AnsibleParam -obj $params -name "name" -type "str" -failifempty $true
$required_version = Get-AnsibleParam -obj $params -name "required_version" -type "str"
$minimum_version = Get-AnsibleParam -obj $params -name "minimum_version" -type "str"
$maximum_version = Get-AnsibleParam -obj $params -name "maximum_version" -type "str"
$repo = Get-AnsibleParam -obj $params -name "repository" -type "str"
$state = Get-AnsibleParam -obj $params -name "state" -type "str" -default "present" -validateset "present", "absent", "latest"
$allow_clobber = Get-AnsibleParam -obj $params -name "allow_clobber" -type "bool" -default $false
$skip_publisher_check = Get-AnsibleParam -obj $params -name "skip_publisher_check" -type "bool" -default $false
$allow_prerelease = Get-AnsibleParam -obj $params -name "allow_prerelease" -type "bool" -default $false
$check_mode = Get-AnsibleParam -obj $params -name "_ansible_check_mode" -default $false

$result = @{changed = $false}

Function Install-NugetProvider {
    Param(
        [Bool]$CheckMode
    )
    $PackageProvider = Get-PackageProvider -ListAvailable | Where-Object {($_.name -eq 'Nuget') -and ($_.version -ge "2.8.5.201")}
    if (-not($PackageProvider)){
        try{
            Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -WhatIf:$CheckMode | out-null
            $result.changed = $true
        }
        catch{
            $ErrorMessage = "Problems adding package provider: $($_.Exception.Message)"
            Fail-Json $result $ErrorMessage
        }
    }
}

Function Install-PrereqModule {
    Param(
        [Bool]$CheckMode
    )

    # Those are minimum required versions of modules.
    $PrereqModules = @{
        PackageManagement = '1.1.7'
        PowerShellGet = '1.6.0'
    }

    ForEach ( $Name in $PrereqModules.Keys ) {

        $ExistingPrereqModule = Get-Module -ListAvailable | Where-Object {($_.name -eq $Name ) -and ($_.version -ge $PrereqModules[$Name] )}

        if ( -not $ExistingPrereqModule ) {
            try {
                Install-Module -Name $Name -MinimumVersion $PrereqModules[$Name] -Force -WhatIf:$CheckMode | Out-Null

                if ( $Name -eq 'PowerShellGet' ) {
                    # An order has to be reverted due to dependency
                    Remove-Module -Name PowerShellGet, PackageManagement -Force
                    Import-Module -Name PowerShellGet, PackageManagement -Force
                }

                $result.changed = $true
            }
            catch{
                $ErrorMessage = "Problems adding a prerequisite module $Name $($_.Exception.Message)"
                Fail-Json $result $ErrorMessage
            }
        }
    }
}

Function Get-PsModule {
    Param(
        [Parameter(Mandatory=$true)]
        [String]$Name,
        [String]$RequiredVersion,
        [String]$MinimumVersion,
        [String]$MaximumVersion
    )

    $props = @{
        Exists = $false
        Version = ""
        Versions = @("")
    }
    $ExistingModule = New-Object -TypeName psobject -Property $props

    $ExistingModules = Get-Module -Listavailable | Where-Object {($_.name -eq $Name)}
    $ExistingModulesCount = $($ExistingModules | Measure-Object).Count

    if ( $ExistingModulesCount -gt 0 ) {

        $ExistingModules | Add-Member -MemberType ScriptProperty -Name FullVersion -Value { "$($this.Version)-$(($this | Select-Object -ExpandProperty PrivateData).PSData.Prerelease)".TrimEnd('-') }

        $ExistingModule.Versions = $ExistingModules.FullVersion

        if ( -not ($RequiredVersion -or
                $MinimumVersion -or
                $MaximumVersion) )  {

            $ReturnedModule = $ExistingModules | Select-Object -First 1
        }
        elseif ( $RequiredVersion ) {
            $ReturnedModule = $ExistingModules | Where-Object -FilterScript { $_.FullVersion -eq $RequiredVersion }
        }
        elseif ( $MinimumVersion -and $MaximumVersion ) {
            $ReturnedModule = $ExistingModules | Where-Object -FilterScript { $MinimumVersion -le $_.Version -and $MaximumVersion -ge $_.Version } | Select-Object -First 1
        }
        elseif ( $MinimumVersion ) {
            $ReturnedModule = $ExistingModules | Where-Object -FilterScript { $MinimumVersion -le $_.Version } | Select-Object -First 1
        }
        elseif ( $MaximumVersion ) {
            $ReturnedModule = $ExistingModules | Where-Object -FilterScript { $MaximumVersion -ge $_.Version } | Select-Object -First 1
        }
    }

    $ReturnedModuleCount = ($ReturnedModule | Measure-Object).Count

    if ( $ReturnedModuleCount -eq 1 ) {
        $ExistingModule.Exists = $true
        $ExistingModule.Version = $ReturnedModule.FullVersion
    }

    $ExistingModule
}

Function Install-PsModule {
    Param(
        [Parameter(Mandatory=$true)]
        [String]$Name,
        [String]$RequiredVersion,
        [String]$MinimumVersion,
        [String]$MaximumVersion,
        [String]$Repository,
        [Bool]$AllowClobber,
        [Bool]$SkipPublisherCheck,
        [Bool]$AllowPrerelease,
        [Bool]$CheckMode
    )

    $ExistingModuleBefore = Get-PsModule -Name $Name -RequiredVersion $RequiredVersion -MinimumVersion $MinimumVersion -MaximumVersion $MaximumVersion

    if ( -not $ExistingModuleBefore.Exists ) {
        try {
            # Install NuGet provider if needed.
            Install-NugetProvider -CheckMode $CheckMode

            $ht = @{
                Name = $Name
                AllowClobber = $AllowClobber
                SkipPublisherCheck = $SkipPublisherCheck
                WhatIf = $CheckMode
                'Force' = $true
            }

            [String[]]$VersionParameters = @("RequiredVersion","MinimumVersion","MaximumVersion")

            ForEach ($VersionParameterString in $VersionParameters) {
                $VersionParameterVariable = Get-Variable -Name $VersionParameterString
                if ( $VersionParameterVariable.Value ){
                        $ht.Add($VersionParameterString,$VersionParameterVariable.Value)
                }
            }

            if ( $AllowPrerelease ) {
                $ht.Add("AllowPrerelease",$AllowPrerelease)
            }

            # If specified, use repository name to select module source.
            if ( $Repository ) {
                $ht.Add("Repository", "$Repository")
            }

            Install-Module @ht -ErrorVariable ErrorDetails | out-null

            $result.changed = $true
        }
        catch {

            if ( $ErrorDetails.Exception.Message ) {
                $ErrorDetailsText = $($ErrorDetails.Exception.Message)
            }
            elseif ( $ErrorDetails.Message ) {
                $ErrorDetailsText = $($ErrorDetails.Message)
            }
            else {
                $ErrorDetailsText = "Unknown"
            }

            $ErrorMessage = "Problems installing $($Name) module: $ErrorDetailsText"
            Fail-Json $result $ErrorMessage
        }
    }
}

Function Remove-PsModule {
    Param(
        [Parameter(Mandatory=$true)]
        [String]$Name,
        [String]$RequiredVersion,
        [String]$MinimumVersion,
        [String]$MaximumVersion,
        [Bool]$CheckMode
    )
    # If module is present, uninstalls it.
    if (Get-Module -Listavailable | Where-Object {$_.name -eq $Name}){
        try{
            $ht = @{
                Name = $Name
                Confirm = $false
                WhatIf = $CheckMode
                Force = $true
            }

            $ExistingModuleBefore = Get-PsModule -Name $Name -RequiredVersion $RequiredVersion -MinimumVersion $MinimumVersion -MaximumVersion $MaximumVersion

            [String[]]$VersionParameters = @("RequiredVersion","MinimumVersion","MaximumVersion")

            ForEach ($VersionParameterString in $VersionParameters) {
                $VersionParameterVariable = Get-Variable -Name $VersionParameterString
                if ( $VersionParameterVariable.Value ){
                        $ht.Add($VersionParameterString,$VersionParameterVariable.Value)
                }
            }

            if ( -not ( $RequiredVersion -or $MinimumVersion -or $MaximumVersion ) ) {
                $ht.Add("AllVersions", $true)
            }

            if ( $ExistingModuleBefore.Exists) {

                Uninstall-Module @ht -ErrorVariable ErrorDetails | out-null

                $result.changed = $true
            }
        }
        catch{
            $ErrorMessage = "Problems removing $($Name) module: $($ErrorDetails.Exception.Message)"
            Fail-Json $result $ErrorMessage
        }
    }
}

Function Find-LatestPsModule {
    Param(
        [Parameter(Mandatory=$true)]
        [String]$Name,
        [String]$Repository,
        [Bool]$AllowPrerelease,
        [Bool]$CheckMode
    )

    try {
        $ht = @{
            Name = $Name
        }

        if ( $AllowPrerelease ) {
            $ht.Add("AllowPrerelease",$AllowPrerelease)
        }

        # If specified, use repository name to select module source.
        if ( $Repository ) {
            $ht.Add("Repository", "$Repository")
        }

        $LatestModule = Find-Module @ht
        $LatestModuleVersion = $LatestModule.Version
    }
    catch {
        $ErrorMessage = "Cant find the module $($Name): $($_.Exception.Message)"
        Fail-Json $result $ErrorMessage
    }

    $LatestModuleVersion
}

# Check PowerShell version, fail if < 5.0
$PsVersion = $PSVersionTable.PSVersion
if ($PsVersion.Major -lt 5 ){
    $ErrorMessage = "Windows PowerShell 5.0 or higher is needed"
    Fail-Json $result $ErrorMessage
}

if ( $required_version -and ( $minimum_version -or $maximum_version ) ) {
       $ErrorMessage = "Parameters required_version and minimum/maximum_version are mutually exclusive."
       Fail-Json $result $ErrorMessage
}

if ( $allow_prerelease -and ( $minimum_version -or $maximum_version ) ) {
    $ErrorMessage = "Parameters minimum_version, maximum_version can't be used with the parameter allow_prerelease."
    Fail-Json $result $ErrorMessage
}

if ( $allow_prerelease -and $state -eq "absent" ) {
    $ErrorMessage = "The parameter allow_prerelease can't be used with state set to 'absent'."
    Fail-Json $result $ErrorMessage
}

if ( ($state -eq "latest") -and
    ( $required_version -or $minimum_version -or $maximum_version ) ) {
        $ErrorMessage = "When the parameter state is equal 'latest' you can use any of required_version, minimum_version, maximum_version."
        Fail-Json $result $ErrorMessage
}

if ( $repo ) {
    $RepositoryExists = Get-PSRepository -Name $repo -ErrorAction Ignore
    if ( $null -eq $RepositoryExists) {
        $ErrorMessage = "The repository $repo doesn't exist."
        Fail-Json $result $ErrorMessage
    }

}

if ( ($allow_clobber -or $allow_prerelease -or
    $required_version -or $minimum_version -or $maximum_version) ) {
    # Update the PowerShellGet and PackageManagement modules.
    # It's required to support AllowClobber, AllowPrerelease parameters.
    Install-PrereqModule -CheckMode $check_mode
}

if ($state -eq "present") {
    if ($name) {
        $ht = @{
            Name = $name
            RequiredVersion = $required_version
            MinimumVersion = $minimum_version
            MaximumVersion = $maximum_version
            Repository = $repo
            AllowClobber = $allow_clobber
            SkipPublisherCheck = $skip_publisher_check
            AllowPrerelease = $allow_prerelease
            CheckMode = $check_mode
        }
        Install-PsModule @ht
    }
}
elseif ($state -eq "absent") {
    if ($name) {
        $ht = @{
            Name = $Name
            CheckMode = $check_mode
            RequiredVersion = $required_version
            MinimumVersion = $minimum_version
            MaximumVersion = $maximum_version
        }
        Remove-PsModule @ht
    }
}
elseif ( $state -eq "latest") {

    $ht = @{
        Name = $Name
        AllowPrerelease = $allow_prerelease
        Repository = $repo
        CheckMode = $check_mode
    }

    $LatestVersion = Find-LatestPsModule @ht

    $ExistingModule = Get-PsModule $Name

    if ( $LatestVersion.Version -ne $ExistingModule.Version ) {

        $ht = @{
            Name = $Name
            RequiredVersion = $LatestVersion
            Repository = $repo
            AllowClobber = $allow_clobber
            SkipPublisherCheck = $skip_publisher_check
            AllowPrerelease = $allow_prerelease
            CheckMode = $check_mode
        }
        Install-PsModule @ht
    }
}

Exit-Json $result
