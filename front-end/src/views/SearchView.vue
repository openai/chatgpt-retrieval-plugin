<script setup lang="ts">
import { ref, onMounted } from 'vue'
import icon_trend from '../assets/icon_trend.svg'
import searchKeywords from './searchKeywords'

const formData = ref({
  searchstring: '',
  temperature: 0.2,
  strictMode: true
})

const resultData = ref<{
  result: { type: string; answers: string; url: string; urlTitle?: string }[]
  kb_html: string
  olh_html: string
  kb_html_old: string
  olh_html_old: string
}>({
  result: [],
  kb_html: '',
  olh_html: '',
  kb_html_old: '',
  olh_html_old: ''
})

const loading = ref(false)

let controller = new AbortController()

const onSubmit = async (e: any) => {
  e.preventDefault()
  if (loading.value) {
    controller?.abort?.()
    controller = new AbortController()
  }
  loading.value = true
  fetch('/query', {
    signal: controller.signal,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      queries: [
        {
          query: formData.value.searchstring
          // filter: {
          //   document_id: 'string',
          //   source: 'email',
          //   source_id: 'string',
          //   author: 'string',
          //   start_date: 'string',
          //   end_date: 'string'
          // },
          // top_k: 3
        }
      ]
    })
  })
    .then((response) => response.json())
    .then((data) => {
      resultData.value = data as any
      loading.value = false
    })
    .catch((error) => {
      if (error.name !== 'AbortError') {
        loading.value = false
        console.error(error)
        alert('Failed to submit.')
      }
    })
}

interface RestaurantItem {
  value: string
}
const restaurants = ref<RestaurantItem[]>([])
const querySearch = (queryString: string, cb: any) => {
  const results = queryString
    ? restaurants.value.filter(createFilter(queryString))
    : restaurants.value
  // call callback function to return suggestions
  cb(results)
}
const createFilter = (queryString: string) => {
  return (restaurant: RestaurantItem) => {
    return restaurant.value.toLowerCase().includes(queryString.toLowerCase())
  }
}
const loadAll = () => searchKeywords

onMounted(() => {
  restaurants.value = loadAll()
})
</script>

<template>
  <main>
    <div class="text-center py-5">
      <img :src="icon_trend" class="icon" />
      <h3>Vision One Document</h3>
    </div>

    <el-form class="w-50" style="margin: 0 auto" :model="formData" @submit="onSubmit">
      <div class="input-group mb-3">
        <el-autocomplete
          v-model="formData.searchstring"
          :fetch-suggestions="querySearch"
          :trigger-on-focus="false"
          class="inline-input w-75"
          clearable
          required
          highlight-first-item
        >
        </el-autocomplete>

        <input type="submit" value="Search" class="btn btn-primary search-button px-4" />
      </div>
      <el-checkbox v-model="formData.strictMode" style="margin-right: 6px" />
      <label class="form-text" for="strictMode" style="font-size: 12px"
        >Answer the question as truthfully as possible</label
      >
      <el-slider v-model="formData.temperature" :min="0" :max="1" :step="0.1" style="width: 50%" />
      <div class="form-text">
        Higher values like 0.8 will make the output more random, while lower values like 0.2 will
        make it more focused and deterministic.
      </div>
    </el-form>
    <template v-if="loading">
      <el-skeleton :rows="20" animated style="margin-top: 50px" />
    </template>
    <template v-if="!loading && resultData.result?.length">
      <template v-for="{ type, url, urlTitle, answers } in resultData.result" :key="type">
        <div class="card my-4">
          <!-- Knowledge Base -->
          <div class="card-header">{{ type === 'kb' ? 'KB' : 'Online Help' }}</div>
          <div class="card-body fs-6">
            <div style="text-align: left">
              <span style="display: inline-block; text-align: left" v-html="answers"> </span>
              <div>
                <span v-if="type === 'kb'" v-html="url"> </span>
                <a v-else :href="url" target="_blank">{{ urlTitle }}</a>
              </div>
            </div>
          </div>
        </div>
      </template>

      <template v-if="resultData.olh_html">
        <h2 class="display-8 text-center mb-4">
          Most Relevant OLH By <span class="text-blue-600">Consine-BM25F</span>
        </h2>
        <div v-html="resultData.olh_html"></div>
      </template>
      <template v-if="resultData.olh_html_old">
        <h2 class="display-8 text-center mb-4">
          Most Relevant OLH By <span class="text-blue-600">Consine Similarity</span>
        </h2>
        <div v-html="resultData.olh_html_old"></div>
      </template>

      <template v-if="resultData.kb_html">
        <h2 class="display-8 text-center mb-4">
          Most Relevant KB By <span class="text-blue-600">Consine-BM25F</span>
        </h2>
        <div v-html="resultData.kb_html"></div>
      </template>
      <template v-if="resultData.kb_html_old">
        <h2 class="display-8 text-center mb-4">
          Most Relevant KB By <span class="text-blue-600">Consine Similarity</span>
        </h2>
        <div v-html="resultData.kb_html_old"></div>
      </template>
    </template>
  </main>
</template>

<style >
.el-input__wrapper {
  padding: 6px 12px;
}
</style>