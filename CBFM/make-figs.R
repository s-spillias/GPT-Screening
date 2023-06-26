library(tidyverse)
library(ggrepel)
library(patchwork)
library(beyonce)
library(ggbeeswarm)

df_fig <- list.files(path = "./Paper-Results", pattern = "FigureImport",
                     full.names = TRUE)

# for(df_file in df_fig){
#   print(df_file)
  supp = ""

df = df_fig %>% lapply(function(x) read.csv(x) %>%
                    mutate(Colab = ifelse(str_detect(x,"Colab"),"Colab","Human"))) %>% 
  bind_rows() %>% 
  mutate(Committee = factor(ifelse(Committee,"Committee","Individual"), levels = c("Individual","Committee")),
         Reflection = factor(ifelse(Reflection,"Reflection","Initial"), levels = c("Initial","Reflection"))) 

#n_paper = df %>% mutate(tot = n_misses + n_extras+ n_finds+ n_omits) %>% pull(tot) %>% 

pal = c("#a6611a",
  "#dfc27d",
  "#80cdc1",
  "#018571")

### Figure 2
df %>% 
  group_by(Reflection,Committee) %>% 
  filter(Colab == "Colab",
         Method == "AI-AnyYes",
         str_detect(Method,'AI')) %>% 
  # mutate(across(starts_with('n_'),min,.names =  "{.col}_min" )) %>% 
  # mutate(across(starts_with('n_'),max,.names =  "{.col}_max" )) %>% 
  # reframe(n_misses_range = paste0(n_misses_min,' - ',n_misses_max),
  #         n_omits_range = paste0(n_omits_min,' - ',n_omits_max),
  #         n_extras_range = paste0(n_extras_min, ' - ',n_extras_max),
  #         n_finds_range = paste0(n_finds_min,' - ',n_finds_max)) %>% 
  distinct() %>% 
  pivot_longer(starts_with('n_'), values_to = 'value',names_to = 'type') %>% 
  mutate(human = factor(ifelse(str_detect(type,"misses|finds"),"Accept","Reject"),levels = c("Accept","Reject")),
         ai = factor(ifelse(str_detect(type,"extras|finds"),"Accept","Reject"),levels = c("Accept","Reject") %>% rev)) %>% 
  ggplot() +
  geom_tile(aes(x = human, y = ai, fill = type)) +
  geom_text(aes(x = human, y = ai, label = value)) +
  xlab("Human") +
  ylab("AI") +
  scale_fill_manual(values = pal[c(2,4,1,4)] #c("tan2","forestgreen","darksalmon","forestgreen")
  ) +
  scale_x_discrete(position = "top") +
 # facet_grid(Reflection~Committee) +
  
  theme_classic() +
  theme(legend.position = "none") 


ggsave(paste0("Figures/Figure2",supp,".png"), device = 'png',height = 3,width = 3)

### Figure 2 SUPP
df %>% 
  group_by(Reflection,Committee) %>% 
  filter(Colab == "Colab",
         str_detect(Method,'AI')) %>% 
  mutate(across(starts_with('n_'),min,.names =  "{.col}_min" )) %>% 
  mutate(across(starts_with('n_'),max,.names =  "{.col}_max" )) %>% 
  reframe(n_misses_range = paste0(n_misses_min,' - ',n_misses_max),
            n_omits_range = paste0(n_omits_min,' - ',n_omits_max),
            n_extras_range = paste0(n_extras_min, ' - ',n_extras_max),
            n_finds_range = paste0(n_finds_min,' - ',n_finds_max)) %>% 
  distinct() %>% 
  pivot_longer(starts_with('n_'), values_to = 'value',names_to = 'type') %>% 
  mutate(human = factor(ifelse(str_detect(type,"misses|finds"),"Accept","Reject"),levels = c("Accept","Reject")),
         ai = factor(ifelse(str_detect(type,"extras|finds"),"Accept","Reject"),levels = c("Accept","Reject") %>% rev)) %>% 
  ggplot() +
  geom_tile(aes(x = human, y = ai, fill = type)) +
  geom_text(aes(x = human, y = ai, label = value)) +
  xlab("Human - Accept") +
  ylab("AI - Accept") +
  scale_fill_manual(values = beyonce_palette(33)[3:6][c(3,1,4,2)] #c("tan2","forestgreen","darksalmon","forestgreen")
                      ) +
  facet_grid(Reflection~Committee) +
  
  theme_classic() +
  theme(legend.position = "none") 
  

ggsave(paste0("Figures/Figure2_supp",supp,".png"), device = 'png',height = 7.59,width = 8.45)

### Figure 3
df_plot = df %>% 
  separate(Method,'id',sep = "_") %>% 
  mutate(tot = n_misses + n_extras+ n_finds+ n_omits) %>% 
  mutate(across(starts_with('n_'), function(x) 100*x/tot)) 

df_colab = df_plot %>% filter(Colab == "Colab")

ggplot(df_plot) +
  geom_point(data = df_colab %>% filter(str_detect(id,"AI")),
             aes(x = n_misses, 
             y = n_extras,
             shape = interaction(Reflection,Committee) ,

             #col = Prompt
             )
             ) +
 geom_point(data = df_colab %>% filter(str_detect(id,"Human")),
            aes(x = n_misses,
                y = n_extras),
            shape = 8, size = 2) +
geom_text_repel(data = df_colab %>% filter(str_detect(id,"Human|AnyYes")),
                aes(label = id, x = n_misses, y = n_extras),box.padding = 0.5,min.segment.length = 0.01) +
  scale_shape_manual(values = c(1,16,2,17),
                     name = "AI - Method") +
  
  scale_color_manual(values = c("black","steelblue")) +
  xlim(0,6.5) +
  ylim(0,6.5) +
  theme_classic() +
 # theme(legend.position = c(0.8,0.5)) +
  xlab("False Negatives (%)") +
  ylab("False Positives (%)") +

df_colab %>% filter(str_detect(id,"AI")) %>% 
  ggplot() +
  aes(x = "AI", 
      y = Kappa) +
 # geom_boxplot(outlier.shape = NA) +
  geom_beeswarm(dodge.width=0.1,cex = 7, method = "swarm",#alpha = 0.1,  position = position_jitter(width = 0.2),
             aes(             shape = interaction(Reflection,Committee)
                             
                           ),
          #   size = 1
             ) +
  geom_point(data = df_colab %>% filter(str_detect(id,"Human")),
             aes(x ="Human",
                 y = Kappa),
             shape = 8, size = 2) +
  geom_text_repel(data = df_colab %>% filter(str_detect(id,"Human")),
                  aes(label = id, x = "Human", y = Kappa),box.padding = 0.5,min.segment.length = 0.01) +
  # geom_text_repel(data = df_colab %>% filter(str_detect(id,"AnyYes")),
  #                 aes(label = id,x = "", y = Kappa),min.segment.length = 0.01) +
  xlab("") +
  scale_shape_manual(values = c(1,16,2,17)) +
  scale_color_manual(values = c("black","steelblue")) +
  theme_classic() +
  theme(legend.position = "none") +

  patchwork::plot_annotation(tag_levels = "a" ) +
  plot_layout(nrow = 2,design = 'aab', heights = c(.6,.4), guides = 'collect')
  
ggsave(paste0("Figures/Figure3",supp,".png"), device = 'png', width = 8.5*.8, height = 4.84*.8)
#}


### Test effect of random string
### Figure S1
count_unique = function(str){
  df_title = list.files(path = "./Paper-Results/rand_test", pattern = str,
                     full.names = TRUE)  %>% 
  lapply(function(x) read.csv(x) %>% as_tibble() %>% 
           dplyr::select(Title,contains("SC")))
 
  df = lapply(df_title, function(x) x %>% dplyr::select(-Title))
  
  title = lapply(df_title, function(x) x %>% dplyr::select(Title))[[1]]
df_count = tibble()
for(i in 1:nrow(df[[1]])){
  for(j in 1:ncol(df[[1]])){
    text = vector()
    for(k in 1:length(df)){
      text = c(text,df[[k]][i,j] %>% as.character)
    }
    
    df_count[i,j] = length(unique(text))
  }
}
out = cbind(title,df_count)
return(out)
}

counts_long = count_unique("False") %>% 
  mutate(rand = "False") %>% 
  bind_rows(
    count_unique("True") %>% 
      mutate(rand = "True")
  ) %>% 
#  setNames(c("Final","Reflection","Initial","Final","Reflection","Initial","Final","Reflection","Initial","RandomString")) %>% 
  pivot_longer(starts_with("..."), names_to = 'names', values_to = "unique_count")

counts = counts_long %>% 
  pivot_wider(values_from = unique_count,names_from = rand)

counts_long %>% 
  ggplot() +
  geom_boxplot(aes(x = rand,y = unique_count)) +
  theme_classic() +
  xlab("Variable Random String") +
  ylab("Number of Unique Responses")

ggsave(paste0("Figures/FigureS1",supp,".png"), device = 'png', width = 8.5*.8, height = 4.84*.8)

# T-Test
result = t.test(counts$False,  counts$True, paired = TRUE)
print(result)

## Figure S2

