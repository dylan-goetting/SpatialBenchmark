import cv2
import numpy as np
from scipy.spatial.transform import Rotation as R
import quaternion
import matplotlib.pyplot as plt
import seaborn as sns


def local_to_global(p, q, local_point):

    pass

def global_to_local(p, q, global_point):

    translated_point = global_point - p

    q_inverse = np.quaternion.conj(q)

    local_point = quaternion.rotate_vectors(q_inverse, translated_point)

    return local_point

def calculate_focal_length(fov_degrees, image_width):

    fov_radians = np.deg2rad(fov_degrees)
    focal_length = (image_width / 2) / np.tan(fov_radians / 2)
    return focal_length

def annotate_image_offline(annotation, image, fov):
            
    local_point = annotation['curr_local_coords']
    point_3d = [local_point[0], -local_point[1], -local_point[2]] #inconsistency between habitat camera frame and classical convention
    focal_length = calculate_focal_length(fov, image.shape[1])
    x = focal_length * point_3d[0] / point_3d[2]
    x_pixel = int(image.shape[1] / 2 + x)

    y =  focal_length * point_3d[1] / point_3d[2]
    y_pixel = int(image.shape[0] / 2 + y)
    label = annotation['obj']
    # Assuming you have an image captured from the sensor
    cv2.circle(image, (x_pixel, y_pixel), 5, (255, 0, 0), -1)
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 1
    font_color = (0, 0, 0)
    font_thickness = 1
    text_size, baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
    text_x = int(x_pixel - text_size[0] // 2)
    text_y = int(y_pixel + text_size[1] + 15)
    rect_top_left = (text_x-3, text_y - text_size[1])  # Top-left corner
    rect_bottom_right = (text_x + text_size[0], text_y + 3)  # Bottom-right corner

    # Draw the rectangle to highlight the background
    cv2.rectangle(image, rect_top_left, rect_bottom_right, (255, 255, 255), -1)
    cv2.putText(image, label, (text_x, text_y), font, font_scale, font_color, font_thickness)

    return image

def plot_correlation_scatter(df, xvar, yvar):
    correlation = df[xvar].corr(df[yvar])

    plt.figure(figsize=(10, 6))
    plt.scatter(df[xvar], df[yvar], alpha=0.5)
    plt.xlabel(xvar)
    plt.ylabel(yvar)
    plt.title(f'Scatter of {xvar} vs {yvar}')

    # Add the correlation label
    plt.text(0.1, max(df[yvar]) * 0.9, f'Correlation: {correlation:.2f}', fontsize=12, ha='left')
    plt.show()

def plot_distribution(df, var, bins=20):
    mean_value = df[var].mean()
    median_value = df[var].median()
    
    plt.figure(figsize=(10, 6))
    plt.hist(df[var], bins=bins, color='blue', alpha=0.7)
    
    # Plot mean and median lines
    plt.axvline(mean_value, color='red', linestyle='dashed', linewidth=1, label=f'Mean: {mean_value:.2f}')
    plt.axvline(median_value, color='green', linestyle='dashed', linewidth=1, label=f'Median: {median_value:.2f}')
    
    # Add labels and title
    plt.xlabel(var)
    plt.ylabel('Frequency')
    plt.title(f'Distribution of {var}')
    
    # Add legend
    plt.legend()
    
    plt.show()

def plot_heatmap(df, xvar, yvar, value):
    heatmap_data = df.pivot_table(index=xvar, columns=yvar, values=value, aggfunc='mean')

    plt.figure(figsize=(10, 8))
    sns.heatmap(heatmap_data, annot=True, cmap='viridis', cbar_kws={'label': value})
    plt.title('Heatmap of Weighted Accuracy')
    plt.show()

def plot_groupby(df, groupby, var, std=True):
    # df['group'] = df['itr'] // 50

    # Group by the new 'group' column
    grouped = df.groupby(groupby)[var]

    # Calculate mean and standard deviation for each group
    mean_accuracy = grouped.mean()
    std_accuracy = grouped.std()

    # Create a bar plot with error bars
    plt.figure(figsize=(10, 6))
    if std:
        plt.bar(mean_accuracy.index, mean_accuracy, yerr=std_accuracy, capsize=5)
        plt.title(f'Mean ± 1 SD of {var} vs groupby')   
    else:
        plt.bar(mean_accuracy.index, mean_accuracy)
        plt.title(f'Mean of {var} vs groupby')   

    plt.xlabel(groupby)
    plt.ylabel(var)
    plt.show()


def plot_results(df, run_name):




    df['x_weighted_accuracy'] = df['x_pts_weighted'] / df['x_possible_pts_weighted']
    df['y_weighted_accuracy'] = df['y_pts_weighted'] / df['y_possible_pts_weighted']
    df['z_weighted_accuracy'] = df['z_pts_weighted'] / df['z_possible_pts_weighted']
    df['overall_weighted_accuracy'] = (df['x_pts_weighted'] + df['y_pts_weighted'] + df['z_pts_weighted']) / (df['x_possible_pts_weighted'] + df['y_possible_pts_weighted'] + df['z_possible_pts_weighted'])

    labels = ['x_weighted_accuracy', 'y_weighted_accuracy', 'z_weighted_accuracy', 'overall_weighted_accuracy']
    values = [
        df['x_weighted_accuracy'].mean(),
        df['y_weighted_accuracy'].mean(),
        df['z_weighted_accuracy'].mean(),
        df['overall_weighted_accuracy'].mean()
    ]

    # Calculate the standard deviations
    errors = [
        df['x_weighted_accuracy'].std(),
        df['y_weighted_accuracy'].std(),
        df['z_weighted_accuracy'].std(),
        df['overall_weighted_accuracy'].std()
    ]

    plt.figure(figsize=(10, 6))
    plt.bar(labels, values, yerr=errors, color=['blue', 'green', 'red', 'purple'], alpha=0.7, capsize=10)
    plt.xlabel('Metrics')
    plt.ylabel('Weighted Accuracy')
    plt.title('Weighted Accuracy for x, y, z and Overall')
    plt.savefig(f'logs/{run_name}/weighted_accuracy.png')
    plt.close()

    plt.figure(figsize=(15, 5))

    plt.subplot(1, 3, 1)
    sns.histplot(df['x_possible_pts_weighted']/df['num_samples'], bins=20, kde=True)
    plt.title('Distribution of x_possible_pts_weighted')

    plt.subplot(1, 3, 2)
    sns.histplot(df['y_possible_pts_weighted']/df['num_samples'], bins=20, kde=True)
    plt.title('Distribution of y_possible_pts_weighted')

    plt.subplot(1, 3, 3)
    sns.histplot(df['z_possible_pts_weighted']/df['num_samples'], bins=20, kde=True)
    plt.title('Distribution of z_possible_pts_weighted')

    plt.tight_layout()
    plt.savefig(f'logs/{run_name}/histograms_possible_pts_weighted.png')
    plt.close()

    # Heatmap showing the accuracy_weighted across the two axes of num_samples and num_objects
    heatmap_data = df.pivot_table(index='num_samples', columns='num_objects', values='accuracy_weighted', aggfunc='mean')

    plt.figure(figsize=(10, 8))
    sns.heatmap(heatmap_data, annot=True, cmap='viridis', cbar_kws={'label': 'Weighted Accuracy'})
    plt.title('Heatmap of Weighted Accuracy')
    plt.savefig(f'logs/{run_name}/heatmap_accuracy_weighted.png')
    plt.close()

    # Error rate plot where success (0 means error)
    error_rate = 1 - df['success'].mean()

    plt.figure(figsize=(6, 4))
    sns.barplot(x=['Error Rate'], y=[error_rate])
    plt.title('Error Rate')
    plt.ylim(0, 1)
    plt.savefig(f'logs/{run_name}/error_rate.png')
    plt.close()

    mean_weighted_accuracy = df.groupby('scene_id')['accuracy_weighted'].mean().reset_index()

    # Plot mean weighted accuracy for each scene
    plt.figure(figsize=(10, 6))
    sns.barplot(x='scene_id', y='accuracy_weighted', data=mean_weighted_accuracy)
    plt.title('Mean Weighted Accuracy for Each Scene')
    plt.xlabel('Scene ID')
    plt.ylabel('Mean Weighted Accuracy')
    plt.ylim(0, 1)
    plt.savefig(f'logs/{run_name}/mean_weighted_accuracy.png')
    plt.close()


    mean_icl_accuracy = df.groupby('icl')['accuracy_weighted'].mean().reset_index()

    plt.figure(figsize=(10, 6))
    sns.barplot(x='icl', y='accuracy_weighted', data=mean_icl_accuracy)
    plt.title('Mean Weighted Accuracy across icl')
    plt.xlabel('num_icl')
    plt.ylabel('Mean Weighted Accuracy')
    plt.ylim(0, 1)
    plt.savefig(f'logs/{run_name}/mean_icl_accuracy.png')
    plt.close()

    df.to_pickle(f'logs/{run_name}/df_results.pkl')