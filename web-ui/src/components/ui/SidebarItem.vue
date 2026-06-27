<template>
    <div>
        <v-tooltip location="right" :open-delay="500" :disabled="navigationStyle !== 'iconsOnly'">
            <template #activator="{ props: activatorProps }">
                <v-list-item
                    :router="to !== undefined"
                    :to="to"
                    :href="href"
                    :target="target"
                    :class="itemClass"
                    v-bind="activatorProps">
                    <template #prepend>
                        <v-icon class="menu-item-icon">{{ icon }}</v-icon>
                    </template>
                    <template v-if="navigationStyle !== 'iconsOnly'" #title>
                        <span class="menu-item-title">{{ title }}</span>
                    </template>
                </v-list-item>
            </template>
            <span>{{ title }}</span>
        </v-tooltip>
        <v-divider v-if="borderBottom" class="my-1" />
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useStore } from 'vuex'
import { useRoute } from 'vue-router'
import type { NaviPoint } from '@/composables/useNavigation'

const props = defineProps({
    item: { type: Object, required: true },
})

const store = useStore()
const route = useRoute()

const navigationStyle = computed(() => store.state.gui.uiSettings.navigationStyle)
const icon = computed(() => (props.item as NaviPoint).icon)
const title = computed(() => (props.item as NaviPoint).title)
const to = computed(() => (props.item as NaviPoint).to ?? undefined)
const href = computed(() => (props.item as NaviPoint).href ?? undefined)
const target = computed(() => (props.item as NaviPoint).target ?? undefined)
const borderBottom = computed(() => false)
const isActive = computed(() => {
    const item = props.item as NaviPoint
    if (item.target === '_blank' || !item.to) return false
    return route.path === item.to
})
const itemClass = computed(() => ({
    'small-list-item': true,
    'active-nav-item': isActive.value,
    'justify-center': navigationStyle.value === 'iconsOnly',
}))
</script>

<style scoped>
.small-list-item {
    height: var(--sidebar-menu-item-height);
}

.justify-center {
    padding-inline: 0 !important;
}

.justify-center:deep(.v-list-item) {
    justify-items: center;
}

.justify-center {
    grid-template-areas: "prepend" !important;
    grid-template-columns: 1fr !important;
}

.justify-center :deep(.v-list-item__prepend) {
    display: flex;
    justify-content: center;
    align-items: center;
    justify-self: center;
    margin-inline-end: 0;
    width: 100%;
}

.justify-center :deep(.v-list-item__spacer) {
    display: none !important;
    width: 0 !important;
    margin: 0 !important;
}

.justify-center :deep(.v-list-item__content) {
    display: none;
}

.active-nav-item {
    background-color: rgba(var(--v-theme-on-surface), 0.12);
}

.menu-item-icon {
    display: flex;
    justify-content: center;
    align-items: center;
    width: auto;
    margin: 0 auto;
    opacity: 0.92;
}

.menu-item-title {
    font-size: 0.8125rem;
    font-weight: 700;
    line-height: 1;
    text-transform: uppercase;
    opacity: 0.88;
}
</style>
