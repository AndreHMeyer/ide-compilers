param(
    [string]$BipidePath = 'D:\Bipide',
    [string]$Manifest = (Join-Path $PSScriptRoot '..\exemplos\bip\casos.json'),
    [string]$Report = (Join-Path $PSScriptRoot '..\docs\validacao_bipide.json')
)

# Usa os binarios originais; nao reimplementa as instrucoes. Execute em Windows
# PowerShell 5.1 (STA). Sem instalar, alterar ou redistribuir o Bipide.
$ErrorActionPreference = 'Stop'
$null = [Reflection.Assembly]::LoadFrom((Join-Path $BipidePath 'BIP.dll'))
$null = [Reflection.Assembly]::LoadFrom((Join-Path $BipidePath 'Classes.dll'))
$null = [Reflection.Assembly]::LoadFrom((Join-Path $BipidePath 'ucBipI.dll'))
$null = [Reflection.Assembly]::LoadFrom((Join-Path $BipidePath 'Fireball.CodeEditor.SyntaxFiles.dll'))
$null = [Reflection.Assembly]::LoadFrom((Join-Path $BipidePath 'Bipide.exe'))
$cases = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$folder = Split-Path -Parent (Resolve-Path -LiteralPath $Manifest)
$results = @()
$flags = [Reflection.BindingFlags]'NonPublic,Public,Instance'
$editor = New-Object Bipide.ucProgramacao
$hostForm = New-Object Windows.Forms.Form
$hostForm.Controls.Add($editor)
$hostForm.ShowInTaskbar = $false
$hostForm.Opacity = 0
$hostForm.Show()
$editor.AddTab([Fireball.CodeEditor.SyntaxFiles.SyntaxLanguage]::ASM, [single]14)
[Windows.Forms.Application]::DoEvents()

try {
foreach ($case in $cases) {
    $assembler = New-Object BIP.Montador.Montador
    $assembler.Configuracoes.RemoverVariaveisNaoUtilizadas = $false
    $code = [IO.File]::ReadAllText((Join-Path $folder $case.assembly))
    $consoleOut = [Console]::Out
    try {
        [Console]::SetOut([IO.TextWriter]::Null) # Parser original imprime rastreamento.
        $accepted = $assembler.Executa($code)
    } finally { [Console]::SetOut($consoleOut) }
    if (-not $accepted -or $assembler.HasError) {
        throw ($case.name + ': erro no montador: ' + ($assembler.ListaErros | Out-String))
    }
    # A rotina REAL da interface converte vetores e resolve enderecos por tamanho.
    # EndMemoria da DLL isolada nao e o mapa usado pelo simulador da aplicacao.
    $editor.CurrentEditor.Document.Text = $code
    try {
        [Console]::SetOut([IO.TextWriter]::Null)
        $accepted = $editor.Executa()
    } finally { [Console]::SetOut($consoleOut) }
    if (-not $accepted) { throw ($case.name + ': compilacao da interface rejeitada') }
    $compiledCode = $editor.parser.objCodigo
    $compiledCode.SetEnderecoRotulosVariavel()

    $simulator = New-Object ucBip.Simulador
    $simulator.setProcessador(4)
    $simType = $simulator.GetType()
    $variables = $compiledCode.GetMemoriaDados()
    $simulator.SetMemoriaDados($variables)
    $simulator.SetMemoriaPrograma($compiledCode.GetMemoriaInstrucao())
    $output = @()
    $inputIndex = 0
    $steps = 0
    $halted = $false
    # O subconjunto emitido e sequencial. O driver fornece cada instrucao
    # montada a seu metodo original; animacoes e botoes nao sao automatizados.
    foreach ($instruction in $compiledCode.GetMemoriaInstrucao()) {
        $op = $instruction.Instrucao.ToUpperInvariant()
        $operand = 0
        if ($instruction.Operando -and -not [int]::TryParse($instruction.Operando, [ref]$operand)) {
            $operand = $simulator.getValorVariavel($instruction.Operando)
        }
        # Faz o verificador original falhar por excecao antes de abrir um dialogo modal.
        if ($op -in @('LDV','STOV')) {
            $simulator.verificaAcessoMemoria($operand, $simType.GetField('_indr', $flags).GetValue($simulator))
        }
        if ($op -eq 'LD' -and $operand -eq 1024) {
            if ($inputIndex -ge $case.inputs.Count) { throw 'Entrada ausente no manifesto' }
            $simType.GetField('in_port', $flags).GetValue($simulator).Text = [string]$case.inputs[$inputIndex]
            # Estado apos confirmacao do usuario; LD ainda le a porta original.
            $simType.GetField('entradaOK', $flags).SetValue($simulator, $true)
            $inputIndex++
        }
        $steps++
        if ($op -eq 'HLT') {
            $before = $simType.GetProperty('_PC', $flags).GetValue($simulator, $null)
            $simulator.HLT(0)
            $after = $simType.GetProperty('_PC', $flags).GetValue($simulator, $null)
            if ($before -ne $after) { throw 'HLT alterou PC' }
            $halted = $true
            break
        }
        if ($op -eq 'NOT') { $simulator.NOT() }
        else { $simulator.$op($operand) }
        if ($op -eq 'STO' -and $operand -eq 1025) {
            $output += $simType.GetField('_outport', $flags).GetValue($simulator)
        }
    }
    if (-not $halted) { throw ($case.name + ': HLT nao alcancado') }
    if ($inputIndex -ne $case.inputs.Count) { throw ($case.name + ': entradas nao consumidas') }
    if (($output -join ',') -ne ($case.outputs -join ',')) {
        throw ($case.name + ': saida [' + ($output -join ',') + '], esperada [' + ($case.outputs -join ',') + ']')
    }
    $verifiedCells = 0
    foreach ($property in $case.memory.PSObject.Properties) {
        $variable = @($variables | Where-Object { $_.Instrucao -eq $property.Name })[0]
        for ($i = 0; $i -lt $property.Value.Count; $i++) {
            $actual = $simulator.getValorMemoria($variable.IndexMemoria + $i)
            if ($actual -ne $property.Value[$i]) {
                throw ($case.name + ': memoria incorreta em ' + $property.Name + '[' + $i + ']')
            }
            $verifiedCells++
        }
    }
    $results += [pscustomobject]@{
        name = $case.name; assembled = $true; halted = $halted; steps = $steps
        inputs = @($case.inputs); outputs = @($output); verifiedMemoryCells = $verifiedCells
    }
    Write-Output ($case.name + ': OK (' + $steps + ' instrucoes; saidas ' + ($output -join ',') + ')')
}
} finally {
    $hostForm.Dispose()
}
$reportData = [pscustomobject]@{
    completedAtUtc = [DateTimeOffset]::UtcNow.ToString('o'); installation = $BipidePath
    method = 'BIP.dll, compilacao real ucProgramacao.Executa/Classes.Codigo e instrucoes originais ucBipI.dll, processador 4; sem automatizar botoes/animacoes.'
    binaries = @(Get-FileHash -LiteralPath (Join-Path $BipidePath 'BIP.dll'), (Join-Path $BipidePath 'ucBipI.dll'), (Join-Path $BipidePath 'Bipide.exe'), (Join-Path $BipidePath 'Classes.dll') -Algorithm SHA256 | Select-Object Path, Hash)
    passed = $results.Count; failed = 0; cases = $results
}
[IO.File]::WriteAllText([IO.Path]::GetFullPath($Report), ($reportData | ConvertTo-Json -Depth 8), (New-Object Text.UTF8Encoding($false)))
Write-Output ('Aprovados: ' + $results.Count + '. Relatorio: ' + $Report)
