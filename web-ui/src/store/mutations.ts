import { MutationTree } from 'vuex'
import { RootState } from './types'

export const mutations: MutationTree<RootState> = {
    setNaviDrawer(state, payload) {
        state.naviDrawer = payload
        localStorage.setItem('naviDrawer', payload)
    },
}
