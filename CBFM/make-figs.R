library(tidyverse)
library(ggrepel)
library(ggalt)
library(patchwork)
library(beyonce)
library(ggbeeswarm)
library(readxl)

file <- "Comparison_Results.xlsx"


  supp = ""

df = c("Human-Compare","Colab-Compare") %>% lapply(function(x) read_excel(file, sheet = x) %>%
                    mutate(Colab = ifelse(str_detect(x,"Colab"),"Colab","Human"))) %>% 
  bind_rows() %>% 
  rename("Name" = "...1") %>% 
  rename("Kappa" = "Kappa Statistic") %>% 
  mutate(Parameters = case_when(str_detect(Name, 'baseline') ~ 'Random String; Temp = 0',
                                str_detect(Name, 'temperature0') ~ 'Constant String; Temp = 0',
                                str_detect(Name, 'temperature') ~ 'Constant String; Temp = 1',
                                str_detect(Name, 'top_p') ~ 'Constant String; top-p = 0.2',
                                str_detect(Name, 'set_seed') ~ 'Constant String; Random Seed; Temp = 0',
                                TRUE ~ '_Human'),
         Model = case_when(str_detect(Name, '3.5-turbo-0301') ~ 'gpt-3.5-turbo-0301; Dec 2023',
                           str_detect(Name, '3.5-turbo-0613') ~ 'gpt-3.5-turbo-0613; Dec 2023',
                           str_detect(Name, '3.5-turbo') ~ 'gpt-3.5-turbo; May 2023',
                           str_detect(Name, 'gpt-4-1106-preview') ~ 'gpt-4-1106-preview; Dec 2023',
                           str_detect(Name, 'gpt-4') ~ 'gpt-4; May 2023',
                           str_detect(Name, "Human") ~ 'Human',
                           TRUE ~ "Not DEFINED"),
         Notation = ifelse(str_detect(Name, "mod"),"Modified SC3",""),
         Committee = factor(ifelse(!str_detect(Name,"Initial|Reflection")|str_detect(Name,"Committee"),"Committee","Individual"), levels = c("Individual","Committee")),
         Reflection = factor(ifelse(!str_detect(Name,"Initial"),"Reflection","Initial"), levels = c("Initial","Reflection")),
         Method = ifelse(str_detect(Name, "AnyYes|_summary| baseline_rand_seed_"),"AnyYes",paste0(Committee,' - ',Reflection))) 
           
#n_paper = df %>% mutate(tot = n_misses + n_extras+ n_finds+ n_omits) %>% pull(tot) %>% 

pal = c("#a6611a",
  "#dfc27d",
  "#80cdc1",
  "#018571")

# Replace with your model ID
model_id <- "CBFM/AI_Output\\May\\gpt-3.5-turbo\\baseline_rand_seed.xlsx - AI - AnyYes" 

# Print column names
print(colnames(df))

### Figure 2
df %>% 
  filter(Name == model_id) %>% 
  filter(Colab == 'Colab') %>% 
  group_by(Reflection,Committee) %>% 
  dplyr::select(-`Kappa`) %>% 
  # filter(Colab == "Colab",
  #        Method == "AI-AnyYes"#,
  #        #str_detect(Method,'AI')
  #        ) %>% 
  distinct() %>% 
  pivot_longer(contains(" "), values_to = 'value',names_to = 'type') %>% 
  mutate(human = factor(ifelse(str_detect(type,"True Positive|False Negative"),"Accept","Reject"),levels = c("Accept","Reject")),
         ai = factor(ifelse(str_detect(type,"False Positive|True Positive"),"Accept","Reject"),levels = c("Accept","Reject") %>% rev)) %>% 
  ggplot() +
  geom_tile(aes(x = human, y = ai, fill = type)) +
  geom_text(aes(x = human, y = ai, label = value)) +
  xlab("Human") +
  ylab("AI") +
  scale_fill_manual(values = pal[c(1,2,4,4)] #c("tan2","forestgreen","darksalmon","forestgreen")
  ) +
  scale_x_discrete(position = "top") +
 # facet_grid(Reflection~Committee) +
  
  theme_classic() +
  theme(legend.position = "none") 


ggsave(paste0("Figures/Figure2",supp,".png"), device = 'png',height = 3,width = 3)

### Figure 2 SUPP
df %>% 
  group_by(Reflection,Committee) %>% 
  #filter(Colab == "Colab",
 #        str_detect(Method,'AI')) %>% 
  #mutate(across(starts_with('n_'),min,.names =  "{.col}_min" )) %>% 
  #mutate(across(starts_with('n_'),max,.names =  "{.col}_max" )) %>% 
  # reframe(n_misses_range = paste0(n_misses_min,' - ',n_misses_max),
  #           n_omits_range = paste0(n_omits_min,' - ',n_omits_max),
  #           n_extras_range = paste0(n_extras_min, ' - ',n_extras_max),
  #           n_finds_range = paste0(n_finds_min,' - ',n_finds_max)) %>% 
  distinct() %>% 
  pivot_longer(starts_with('n_'), values_to = 'value',names_to = 'type') %>% 
  mutate(human = factor(ifelse(str_detect(type,"True Positive|False Negative"),"Accept","Reject"),levels = c("Accept","Reject")),
         ai = factor(ifelse(str_detect(type,"False Positive|True Negative"),"Accept","Reject"),levels = c("Accept","Reject") %>% rev)) %>% 
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

####################################
####################################
### Figure 3

model_pal = c("black","steelblue","pink","forestgreen",'orange') %>% rev()
shape_pal = c(19,1,15,0,17) %>% rev()

df_plot = df %>% 
  #separate(Method,'id',sep = "_") %>% 
  mutate(tot = `True Positive` + `True Negative` + `False Positive` + `False Negative`) %>% 
  mutate(across(contains(' '), function(x) 100*x/tot)) %>% 
  dplyr::select(-tot)

df_colab = df_plot %>% 
  filter(Colab == "Colab") #%>% 
  #filter(Reflection == "Reflection",Committee == "Committee")
 # filter(str_detect(Parameters, "Random String|Not DEFINED"))

ggplot(df_plot) +
  geom_point(data = df_colab %>% filter(str_detect(Model,"gpt")),
             aes(x = `False Negative`, 
             y = `False Positive`,
             col = Model,
             #fill = Model,
             shape = Method,
             # col = Parameters

             #col = Prompt
             ),
             size = 2,
             stroke = 1,
             #alpha = 0.5
             ) +
 # geom_encircle(data = df_colab %>% filter(str_detect(Model,"gpt")),
 #               s_shape = 1, expand = 0,
 #               aes(x = `False Negative`, 
 #                   y = `False Positive`, group = Model, col = Model)) +
  geom_point(data = df_colab %>% filter(str_detect(Notation,"Modified")),
                #s_shape = 0, expand = 0,
                aes(x = `False Negative`, 
                    y = `False Positive`), col = 'red', size = 0.5) +
 geom_point(data = df_colab %>% filter(str_detect(Model,"Human")),
            aes(x = `False Negative`,
                y = `False Positive`),
            shape = 8, size = 2) +
geom_text_repel(data = df_colab %>% filter(str_detect(Model,"Human")),
                aes(label = Model, x = `False Negative`, y = `False Positive`),box.padding = 0.5,min.segment.length = 0.01) +
  geom_text_repel(data = df_colab %>% filter(str_detect(Notation,"Mod")),
                  aes(label = Notation,x = `False Negative`, y = `False Positive`),box.padding = 0.5,min.segment.length = 0.01,size = 3) +
  scale_shape_manual(values = shape_pal,
                     name = "AI - Method") +
  scale_shape_manual(values = shape_pal,name = "AI - Method") +
  scale_color_manual(values = model_pal) +
  scale_fill_manual(values = model_pal) +
  xlim(0,5) +
  ylim(0,6.5) +
  theme_classic() +
  theme(
        axis.title.y = element_text(margin = margin(t = 0, r =-300, b = 0, l = 0))) +
 # theme(legend.position = c(0.8,0.5)) +
  xlab("False Negatives (%)") +
  ylab("False Positives (%)") +

df_colab %>% filter(str_detect(Model,"gpt"),Method == 'AnyYes') %>% 
  ggplot() +
  aes(x = Parameters, 
      y = Kappa) +
 # geom_boxplot(outlier.shape = NA) +
  geom_hline(yintercept = (df_colab %>% filter(str_detect(Model,"Human")))$Kappa,
                linetype = 3
                 ) +
  geom_point(#dodge.width=0.0,
              #  cex = 0, method = "swarm",#alpha = 0.1,  position = position_jitter(width = 0.2),
             aes(#interaction(Reflection,Committee), 
                 shape = Method,
                 col = Model,
                 #fill = Model,
                             
                           ),
             #alpha = 0.5,
             size = 2, stroke = 1
          #   size = 1
             ) +

  geom_point(data = df_colab  %>% filter(str_detect(Notation,"Modified")),
             aes(x =Parameters,
                 y = Kappa),
             #shape = 8, 
             size = 0.5, col = "red") +
  geom_text_repel(data = df_colab %>% filter(str_detect(Model,"Human")),
                  aes(label = Model, x = 0, y = Kappa),box.padding = 0.5,min.segment.length = 0.05) +
  geom_text_repel(data = df_colab %>% filter(str_detect(Notation,"Mod")),
                  aes(label = Notation, x = Parameters, y = Kappa),box.padding = 0.5,min.segment.length = 0.01,size = 3) +
  # geom_text_repel(data = df_colab %>% filter(str_detect(id,"AnyYes")),
  #                 aes(label = id,x = "", y = Kappa),min.segment.length = 0.01) +
  xlab("") +
  ylim(0.2,1) +
  scale_shape_manual(values = shape_pal,name = "AI - Method") +
  scale_color_manual(values = model_pal) +
  scale_fill_manual(values = model_pal) +
  theme_classic() +
  theme(legend.position = "none") +
  coord_flip() +
  patchwork::plot_annotation(tag_levels = "a" ) +
  plot_layout(nrow = 2,design = 'aa\nbb', heights = c(.7,.3), guides = 'collect')

scaler = 1.0

ggsave(paste0("Figures/Figure3",supp,".png"), device = 'png', width = 8.5*scaler, height = 4.84*scaler)
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

counts_long = count_unique("gpt") %>% 
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

