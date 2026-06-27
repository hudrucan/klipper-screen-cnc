import router from '@/plugins/router'
import { ActionTree } from 'vuex'
import { ConfigJson, RootState } from './types'

export const actions: ActionTree<RootState, RootState> = {
    switchToDashboard() {
        if (router.currentRoute.fullPath !== '/') router.push('/')
    },

    setNaviDrawer({ commit }, payload) {
        commit('setNaviDrawer', payload)
    },

    /**
     * This function will parse the config.json content and config mainsail
     */
    async importConfigJson({ commit }, payload: ConfigJson) {
        if (payload.hostname) commit('socket/setData', { hostname: payload.hostname })
        if (payload.port) commit('socket/setData', { port: parseInt(payload.port.toString()) })
        if (payload.path) commit('socket/setData', { route_prefix: payload.path })
    },
}
