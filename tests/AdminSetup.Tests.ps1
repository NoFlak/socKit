#requires -Version 5.1
# Pester tests for AdminSetup module
# Use: Invoke-Pester -Script .\tests\AdminSetup.Tests.ps1

Import-Module "$PSScriptRoot\..\AdminSetup\AdminSetup.psm1" -Force

Describe 'AdminSetup Module' {

  Context 'Test-AdminPrereqs' {
    It 'Returns structured object when non-admin' {
      Mock -CommandName Test-IsAdmin -MockWith { $false }
      $res = Test-AdminPrereqs
      $res | Should -Not -BeNullOrEmpty
      $res.Success | Should -BeFalse
      $res.Reasons | Should -Contain 'Not running with administrative privileges.'
    }

    It 'Returns structured object when admin' {
      Mock -CommandName Test-IsAdmin -MockWith { $true }
      $res = Test-AdminPrereqs
      $res.Success | Should -BeTrue
      $res.IsAdmin | Should -BeTrue
    }
  }

  Context 'Idempotency' {
    It 'Skips install when feature already present (Server)' {
      Mock -CommandName Get-IsServerOS -MockWith { $true }
      Mock -CommandName Get-WindowsFeature -MockWith { [pscustomobject]@{ Name='Web-Server'; Installed=$true } }
      Mock -CommandName Install-WindowsFeature -Verifiable

      $sum = Install-Features -Feature 'Web-Server' -DryRun:$false
      ($sum.Actions | Where-Object { $_.Action -eq 'AlreadyPresent' }).Count | Should -Be 1
      Assert-MockCalled Install-WindowsFeature -Times 0
    }
  }

  Context 'DryRun' {
    It 'Does not call install cmdlets when DryRun' {
      Mock -CommandName Get-IsServerOS -MockWith { $true }
      Mock -CommandName Get-WindowsFeature -MockWith { [pscustomobject]@{ Name=$args[0]; Installed=$false } }
      Mock -CommandName Install-WindowsFeature -Verifiable
      Mock -CommandName Invoke-Expression -MockWith { throw 'Invoke-Expression should not be called during DryRun' }

      $sum = Install-Features -Feature 'Web-Server' -DryRun
      ($sum.Actions | Where-Object { $_.Result -eq 'Preview' }).Count | Should -Be 1
      Assert-MockCalled Install-WindowsFeature -Times 0
    }
  }

  Context 'Interactive CSV validation' {
    It 'Identifies malformed CSV rows and returns errors (no installs)' {
      Mock -CommandName Read-Host -MockWith { 'dummy.csv' }
      Mock -CommandName Import-Csv -MockWith {
        @(
          [pscustomobject]@{ Target='HOST1'; Features=''; Profile='server-core' }, # missing features
          [pscustomobject]@{ Target=''; Features='DNS;DHCP'; Profile='server-core' } # missing target
        )
      }
      $preview = Install-Features -Interactive -DryRun
      $preview.Validation | Should -Be 'Failed'
      $preview.Errors.Count | Should -BeGreaterThan 0
    }
  }

  Context 'Logging' {
    It 'Writes JSON artifact summary (mocked Set-Content)' {
      Mock -CommandName Get-IsServerOS -MockWith { $true }
      Mock -CommandName Get-WindowsFeature -MockWith { [pscustomobject]@{ Name=$args[0]; Installed=$false } }
      Mock -CommandName Install-WindowsFeature
      $called = $false
      Mock -CommandName Set-Content -ParameterFilter { $Path -like '*\ProgramData\AdminSetup\artifacts\*\summary.json' } -MockWith { $script:called = $true }
      $null = Install-Features -Feature 'Web-Server' -DryRun
      $script:called | Should -BeTrue
    }
  }
}

