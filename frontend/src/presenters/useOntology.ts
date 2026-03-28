import { useEffect } from 'react'
import api from './api'
import { useOntologyStore } from '../models/ontologyStore'

export function useOntology() {
  const {
    objects, links, rules, summary, loading,
    setObjects, setLinks, setRules, setSummary, setLoading, updateRule,
  } = useOntologyStore()

  useEffect(() => {
    fetchAll()
  }, [])

  async function fetchAll() {
    setLoading(true)
    try {
      const [objRes, linkRes, ruleRes, sumRes] = await Promise.all([
        api.get('/api/v1/ontology/objects'),
        api.get('/api/v1/ontology/links'),
        api.get('/api/v1/ontology/rules'),
        api.get('/api/v1/ontology/summary'),
      ])
      setObjects(objRes.data)
      setLinks(linkRes.data)
      setRules(ruleRes.data)
      setSummary(sumRes.data)
    } catch (e) {
      console.error('온톨로지 로드 실패:', e)
    } finally {
      setLoading(false)
    }
  }

  async function toggleRule(id: string, enabled: boolean) {
    try {
      await api.patch(`/api/v1/ontology/rules/${id}`, { enabled })
      updateRule(id, { enabled })
    } catch (e) {
      console.error('규칙 수정 실패:', e)
    }
  }

  async function patchRule(id: string, patch: { condition?: Record<string, unknown>; action_params?: Record<string, unknown>; priority?: number }) {
    try {
      const res = await api.patch(`/api/v1/ontology/rules/${id}`, patch)
      updateRule(id, res.data)
    } catch (e) {
      console.error('규칙 수정 실패:', e)
    }
  }

  return { objects, links, rules, summary, loading, refetch: fetchAll, toggleRule, patchRule }
}
