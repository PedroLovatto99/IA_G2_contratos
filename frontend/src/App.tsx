import { useState, type FormEvent } from 'react'

const URL_API = 'http://localhost:8000'

type PontoDeAtencao = {
  clausula: string
  problema: string
  gravidade: 'alta' | 'media' | 'baixa'
  fundamento: string
}

const GRAVIDADES = {
  alta: { texto: 'Alta', cor: 'bg-red-100 text-red-800' },
  media: { texto: 'Média', cor: 'bg-amber-100 text-amber-800' },
  baixa: { texto: 'Baixa', cor: 'bg-blue-100 text-blue-800' },
}

function App() {
  const [arquivo, setArquivo] = useState<File | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState('')
  const [pontos, setPontos] = useState<PontoDeAtencao[] | null>(null)

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (!arquivo) return

    setCarregando(true)
    setErro('')
    setPontos(null)

    const dados = new FormData()
    dados.append('arquivo', arquivo)

    try {
      const resposta = await fetch(`${URL_API}/avaliar`, { method: 'POST', body: dados })
      const corpo = await resposta.json().catch(() => null)

      if (resposta.ok) {
        setPontos(corpo.pontos_de_atencao)
      } else {
        setErro(typeof corpo?.detail === 'string' ? corpo.detail : 'Não foi possível analisar o contrato.')
      }
    } catch {
      setErro('Não foi possível conectar ao servidor.')
    } finally {
      setCarregando(false)
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-3xl font-bold text-slate-900">ContratosCheck</h1>
      <p className="mt-2 text-slate-600">Envie um contrato e veja os pontos de atenção com base na legislação brasileira.</p>

      <form onSubmit={enviar} className="mt-8 rounded-lg border border-slate-200 bg-white p-6">
        <label htmlFor="arquivo" className="block font-medium text-slate-900">
          Contrato em PDF ou DOCX
        </label>
        <input
          id="arquivo"
          type="file"
          accept=".pdf,.docx"
          onChange={(evento) => setArquivo(evento.target.files?.[0] ?? null)}
          className="mt-2 block w-full text-slate-700 file:mr-4 file:rounded-md file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-slate-900 hover:file:bg-slate-200"
        />
        <button
          type="submit"
          disabled={!arquivo || carregando}
          className="mt-4 rounded-md bg-slate-900 px-4 py-2 font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {carregando ? 'Analisando...' : 'Analisar contrato'}
        </button>
      </form>

      {erro && (
        <p role="alert" className="mt-6 rounded-md bg-red-50 p-4 text-red-800">
          {erro}
        </p>
      )}

      <section aria-live="polite" className="mt-8">
        {pontos?.length === 0 && <p className="text-slate-700">Nenhum ponto de atenção encontrado.</p>}

        {pontos && pontos.length > 0 && (
          <>
            <h2 className="text-xl font-semibold text-slate-900">Pontos de atenção ({pontos.length})</h2>
            <ul className="mt-4 space-y-4">
              {pontos.map((ponto, indice) => (
                <li key={indice} className="rounded-lg border border-slate-200 bg-white p-5">
                  <span className={`rounded-full px-3 py-1 text-sm font-medium ${GRAVIDADES[ponto.gravidade].cor}`}>
                    Gravidade: {GRAVIDADES[ponto.gravidade].texto}
                  </span>
                  <blockquote className="mt-4 border-l-4 border-slate-300 pl-4 text-slate-600 italic">
                    {ponto.clausula}
                  </blockquote>
                  <p className="mt-3 text-slate-900">{ponto.problema}</p>
                  <p className="mt-3 text-sm text-slate-600">
                    <strong>Fundamento:</strong> {ponto.fundamento}
                  </p>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </main>
  )
}

export default App
